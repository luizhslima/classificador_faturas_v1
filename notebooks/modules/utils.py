import pytesseract
from pytesseract import Output
from pdf2image import convert_from_path
import re
import os


from minio import Minio
from minio.error import S3Error


def gerar_prompt_classificacao(caminho_arquivo: str, transacao: dict, categorias: list) -> str:
    """
    Extrai metadados do caminho do datalake e gera o prompt dinâmico para a LLM.
    """
    
    # 1. Extrair a fonte do banco (ex: "nubank" a partir de "source=nubank")
    match_source = re.search(r"source=([^/]+)", caminho_arquivo)
    banco_origem = match_source.group(1).capitalize() if match_source else "Desconhecido"
    
    # 2. Descobrir se é arquivo nativo (digital) ou imagem (OCR)
    _, extensao = os.path.splitext(caminho_arquivo)
    extensao = extensao.lower()
    
    is_digital = extensao in ['.csv', '.ofx', '.json', '.txt']
    
    # 3. Definir as regras dinâmicas com base na origem
    if is_digital:
        tipo_extracao = f"Arquivo digital nativo ({extensao})"
        regra_ocr = (
            "NÃO presuma erros tipográficos ou de OCR. A descrição recebida é exatamente "
            "como o lojista ou autônomo cadastrou o nome fantasia na maquininha/gateway. "
            "Nomes incomuns não são erros de leitura, são apenas nomes informais."
        )
    else:
        tipo_extracao = f"Extração óptica/imagem ({extensao})"
        regra_ocr = (
            "Considere possíveis erros de leitura de caracteres (OCR), pois a origem "
            "é uma imagem ou PDF escaneado (ex: 'l' no lugar de '1', espaços extras)."
        )

    # 4. Formatar a lista de categorias (reaproveitando sua lógica)
    categorias_formatadas = ';\n'.join([f"Nome:{tipo['nome']} - descrição: {tipo['descricao']}" for tipo in categorias])

    # 5. Montar o System Prompt Dinâmico
    system_prompt = f"""Você é um assistente financeiro especialista em classificar transações de faturas de cartão de crédito no Brasil.

CONTEXTO DA EXTRAÇÃO:
- Banco Origem: {banco_origem}
- Formato do Dado: {tipo_extracao}

REGRAS DE ANÁLISE:
1. PROCESSADORES DE PAGAMENTO: Prefixos como "PG*", "PAG*", "MP*", "ZOOP*", "SUMUP*" indicam apenas a maquininha/gateway. Descodifique siglas comuns (IFD, UBR, AMZN).
2. COMBATE A ALUCINAÇÕES: Não invente marcas ou aplicativos. Se você não reconhecer o estabelecimento com certeza absoluta baseada em fatos reais, não tente forçar um encaixe.
3. REGRA DE ORIGEM DO DADO: {regra_ocr}
4. ESTABELECIMENTOS DESCONHECIDOS: Se a transação for ambígua, um nome próprio informal (ex: 'jhoonymorango'), ou apenas um gateway genérico, defina 'requer_confirmacao=true' e use confiança baixa (<=0.70).
5. CADEIA DE PENSAMENTO: Pense passo a passo. Gere o campo "raciocinio" ANTES de gerar a "categoria".

CATEGORIAS PERMITIDAS (Você DEVE escolher apenas uma desta lista):
{categorias_formatadas}
"""
    
    return system_prompt


def extrair_metadados_datalake(caminho_arquivo: str) -> dict:
    """
    Extrai metadados estruturados a partir do caminho do arquivo no datalake.
    Exemplo de entrada: bronze/source=nubank/year=2026/month=08/day=09/66ba1c62-5895-4d78-af34-ef4844bac960/original.csv
    """
    metadados = {
        "camada": None,
        "source": None,
        "year": None,
        "month": None,
        "day": None,
        "uuid": None,
        "nome_arquivo": None,
        "extensao": None,
        "is_digital_nativo": True
    }
    
    # 1. Extrair nome e extensão do arquivo
    nome_arquivo = os.path.basename(caminho_arquivo)
    _, extensao = os.path.splitext(nome_arquivo)
    
    metadados["nome_arquivo"] = nome_arquivo
    metadados["extensao"] = extensao.lower()
    
    # Define se é um formato estruturado (digital) ou imagem (possível OCR)
    metadados["is_digital_nativo"] = metadados["extensao"] in ['.csv', '.ofx', '.json', '.txt', '.xml']
    
    # 2. Extrair informações da estrutura de pastas
    partes = caminho_arquivo.split('/')
    if len(partes) > 1:
        metadados["camada"] = partes[0]
        metadados["uuid"] = partes[-2] # Pega o diretório pai do arquivo (o UUID)
    
    # 3. Extrair as partições chave=valor (ex: source=nubank, year=2026) usando Regex
    particoes = re.findall(r"([a-zA-Z0-9_]+)=([a-zA-Z0-9_-]+)", caminho_arquivo)
    for chave, valor in particoes:
        metadados[chave] = valor
        
    return metadados


def gerar_regra_ocr(is_digital_nativo: bool) -> str:
    """
    Retorna a instrução específica para a LLM baseada na possibilidade de erro de OCR.
    """
    if is_digital_nativo:
        return (
            "ATENÇÃO - ARQUIVO DIGITAL NATIVO: NÃO presuma erros tipográficos ou de leitura (OCR). "
            "A descrição recebida é EXATAMENTE como o lojista ou autônomo cadastrou o nome fantasia na maquininha ou gateway. "
            "Nomes incomuns ou aglutinados (ex: 'jhoonymorango') não são erros, são apenas nomes informais. "
            "Não invente empresas, aplicativos ou marketplaces para justificar nomes estranhos."
        )
    else:
        return (
            "ATENÇÃO - EXTRAÇÃO POR OCR/IMAGEM: Considere a possibilidade de erros de leitura de caracteres (OCR), "
            "pois a origem do dado é uma imagem escaneada. É comum que letras sejam trocadas (ex: 'l' por '1', 'o' por '0') "
            "ou que espaços sejam omitidos. Você pode ajustar pequenas variações de caracteres para identificar o "
            "estabelecimento, mas evite alucinar marcas que não correspondam à string."
        )

def extrair_texto_avancado(caminho_pdf):
    print(f"Processando: {caminho_pdf}")
    texto_final_fatura = []
    
    # Configuração Customizada do Tesseract (Direto do README)
    # OEM 3: Usa a rede neural LSTM padrão do Tesseract
    # PSM 6: Assume um bloco de texto uniforme (ótimo para tabelas de faturas)
    config_tesseract = r'--oem 3 --psm 6'
    
    try:
        imagens_paginas = convert_from_path(caminho_pdf, dpi=300)
        
        for num_pagina, imagem in enumerate(imagens_paginas):
            print(f"Lendo Página {num_pagina + 1}...")
            
            # Usando image_to_data (Retorna um DataFrame do Pandas)
            # Timeout de 60 segundos para evitar travamentos
            dados_ocr = pytesseract.image_to_data(
                imagem, 
                lang='por', 
                config=config_tesseract, 
                output_type=Output.DATAFRAME,
                timeout=60
            )
            
            # Limpeza rápida: Remover valores vazios e espaços em branco
            dados_ocr = dados_ocr.dropna(subset=['text'])
            dados_ocr = dados_ocr[dados_ocr['text'].str.strip() != '']
            
            # FILTRO DE CONFIANÇA (O pulo do gato para o ByT5)
            # Só pega palavras que o OCR tem mais de 40% de certeza
            # Isso evita mandar "lixo visual" irrecuperável para o ByT5
            palavras_confiaveis = dados_ocr[dados_ocr['conf'] > 40]['text'].tolist()
            
            # Junta as palavras de volta em uma string separada por espaços
            texto_limpo = " ".join(palavras_confiaveis)
            texto_final_fatura.append(texto_limpo)
            
        return "\n".join(texto_final_fatura)

    except pytesseract.TesseractError:
        return "Erro: O Tesseract demorou muito e foi interrompido (Timeout)."
    except Exception as e:
        return f"Erro crítico: {e}"


def normalizar_nome(nome: str) -> str:
    texto = nome.lower()

    # NOVO: Remove repetições exatas em volta de um asterisco (ex: "tim*tim" vira "tim")
    texto = re.sub(r"\b([a-z]+)\*\1\b", r"\1", texto)

    # Remove termos comuns de pagamentos e naturezas jurídicas
    texto = re.sub(r"\b(pag|pix|compra|debito|credito)\b\*?", "", texto)
    texto = re.sub(r"\b(ltda|me|epp|sa|s/a|eireli)\b", " ", texto)

    # Mantém apenas letras, números e espaços (aqui o * que sobrou vira espaço)
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    
    # Remove números com 4 ou mais dígitos
    texto = re.sub(r"\b\d{4,}\b", " ", texto)

    # Remove espaços extras
    texto = re.sub(r"\s+", " ", texto).strip()
    
    return texto

def conectar_minio(
    endpoint="192.168.15.18:9000",
    access_key="admin_tcc",
    secret_key="senha_super_segura",
    secure=False,
):
    """
    Cria e retorna um cliente conectado ao MinIO.

    :param endpoint: host:porta do servidor MinIO (sem http/https)
    :param access_key: chave de acesso
    :param secret_key: chave secreta
    :param secure: True para HTTPS, False para HTTP
    :return: instância de Minio ou None em caso de erro
    """
    try:
        client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        # Testa a conexão listando os buckets
        client.list_buckets()
        print("Conexão com MinIO estabelecida com sucesso!")
        return client
    except S3Error as e:
        print(f"Erro ao conectar no MinIO: {e}")
        return None