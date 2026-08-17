import re
import io
import warnings
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat, DocumentStream

warnings.filterwarnings("ignore")

# ─── Constantes e Ajustes para OCR ────────────────────────────────────────────

MESES_PT = {
    "JAN": "01", "FEV": "02", "MAR": "03", "ABR": "04",
    "MAI": "05", "JUN": "06", "JUL": "07", "AGO": "08",
    "SET": "09", "OUT": "10", "NOV": "11", "DEZ": "12",
}

OCR_MESES_CORRECAO = {
    "MAL": "MAI", "MAl": "MAI", "MA1": "MAI", 
    "JUI": "JUL", "JU1": "JUL",
    "ABP": "ABR", "0UT": "OUT", "OUT": "OUT"
}

# Regex para Metadados e Fallbacks
RE_DATA    = re.compile(r"^(\d{2})\s+([A-Za-z]{3})$")
RE_DETALHE = re.compile(r"(\d{4})\s+(.+?)\s+R\$\s*([\d.,]+)$")
RE_PARCELA = re.compile(r"\s*-\s*Parcela\s+(\d+/\d+)", re.IGNORECASE)

# 🚀 NOVA REGEX PARA TABELAS:
# Captura a linha inteira (ex: "01 MAI | 6039 | Drogaria - Parcela 3/3 | R$ 140,95")
RE_LINHA_TABELA = re.compile(
    r"\|?\s*(\d{2})\s+([A-Za-z]{3})\s*\|?\s*(?:.*?)(\d{4})\s*\|?\s*(.+?)\s*\|?\s*R\$\s*([\d.,]+)"
)

def valor_float(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def extrair_paginas_texto(converter:DocumentConverter, pdf_stream: io.BytesIO, filename: str = "fatura.pdf") -> dict[int, list[tuple[float, str]]]:
    """
    Exporta o documento para Markdown, o que formata perfeitamente as tabelas
    sem precisarmos iterar sobre coordenadas ou células individuais.
    """

    conv = converter.convert(DocumentStream(name=filename, stream=pdf_stream))
    doc = conv.document
    
    # ── MÁGICA DO DOCLING V2 ──────────────────────────────────────────────────
    # O modelo converte as TableItems estruturadas utilizando "|".
    # Transformamos tudo em um array de linhas.
    texto_md = doc.export_to_markdown()
    
    # Colocamos tudo na "página 1" para compatibilidade com o resto do código, 
    # já que a leitura contínua (Top-Down) está garantida pelo export.
    paginas = {1: []}
    for y_dummy, linha in enumerate(texto_md.split("\n")):
        linha_limpa = linha.strip()
        if linha_limpa:
            paginas[1].append((float(y_dummy), linha_limpa))

    return paginas


def extrair_metadados(paginas: dict) -> dict:
    """Extrai cabeçalho da fatura."""
    texto_total = "\n".join(t for linhas in paginas.values() for _, t in linhas)
    meta = {}

    m = re.search(r"Olá,\s+(\w+)", texto_total)
    if m:
        meta["titular"] = m.group(1)

    m = re.search(r"no valor de\s+R\$\s*([\d.,]+)", texto_total)
    if m:
        meta["total_fatura"] = valor_float(m.group(1))

    m = re.search(r"Data de vencimento:\s+(\d{2})\s+([A-Za-z]{3})\s+(\d{4})", texto_total)
    if m:
        dia, mes_raw, ano = m.group(1), m.group(2).upper(), m.group(3)
        mes_corrigido = OCR_MESES_CORRECAO.get(mes_raw, mes_raw)
        meta["vencimento"] = f"{ano}-{MESES_PT.get(mes_corrigido, '00')}-{dia}"
        meta["_vcto_ano"]  = int(ano)
        meta["_vcto_mes"]  = int(MESES_PT.get(mes_corrigido, "01"))

    m = re.search(r"Período vigente:\s+([\w ]+)\s+a\s+([\w ]+)", texto_total)
    if m:
        meta["periodo_inicio"] = m.group(1).strip()
        meta["periodo_fim"]    = m.group(2).strip()

    return meta


def inferir_ano(mes_str: str, vcto_ano: int, vcto_mes: int) -> int:
    mes_num = int(MESES_PT.get(mes_str, "01"))
    return vcto_ano - 1 if mes_num > vcto_mes else vcto_ano


def extrair_transacoes(paginas: dict, meta: dict) -> list[dict]:
    vcto_ano = meta.get("_vcto_ano", 2026)
    vcto_mes = meta.get("_vcto_mes", 6)

    transacoes = []
    dentro_secao = False
    data_pendente = None

    for pg_num in sorted(paginas.keys()):
        linhas = paginas[pg_num]

        for _, texto in linhas:

            # ── Detecta início e fim da seção ─────────────────────────────────
            if "TRANSAÇÕES" in texto.upper():
                dentro_secao = True
                continue

            if not dentro_secao:
                continue

            if "PAGAMENTOS E FINANCIAMENTOS" in texto.upper():
                dentro_secao = False
                break

            # ── Tentativa 1: O Docling renderizou a linha como Tabela ─────────
            m_tab = RE_LINHA_TABELA.search(texto)
            if m_tab:
                dia = m_tab.group(1)
                mes_raw = m_tab.group(2).upper()
                mes_corrigido = OCR_MESES_CORRECAO.get(mes_raw, mes_raw)

                cartao = m_tab.group(3)
                desc_raw = m_tab.group(4).strip()
                valor_str = m_tab.group(5)

                # Limpa pipes ( | ) que sobram na extração do layout da tabela
                desc_raw = desc_raw.replace("|", "").strip()

                parcela = None
                m_parc = RE_PARCELA.search(desc_raw)
                if m_parc:
                    parcela  = m_parc.group(1)
                    desc_raw = RE_PARCELA.sub("", desc_raw).strip()

                ano = inferir_ano(mes_corrigido, vcto_ano, vcto_mes)
                mes_num = MESES_PT.get(mes_corrigido, "01")
                data_iso = f"{ano}-{mes_num}-{dia}"

                transacoes.append({
                    "data":         data_iso,
                    "cartao_final": cartao,
                    "descricao":    desc_raw,
                    "parcela":      parcela,
                    "valor":        valor_float(valor_str),
                })
                
                data_pendente = None # Zera o estado do Fallback
                continue

            # ── Tentativa 2 (Fallback): Caso não vire tabela e saia na mesma linha
            m_inline = re.match(r"^(\d{2})\s+([A-Za-z]{3})\s+(.*)$", texto)
            if m_inline and RE_DETALHE.search(m_inline.group(3)):
                mes_raw = OCR_MESES_CORRECAO.get(m_inline.group(2).upper(), m_inline.group(2).upper())
                data_pendente = (m_inline.group(1), mes_raw)
                texto = m_inline.group(3) 
            else:
                # ── Tentativa 3 (Fallback Original): Linhas isoladas de data e compra
                m_data = RE_DATA.match(texto)
                if m_data:
                    mes_raw = OCR_MESES_CORRECAO.get(m_data.group(2).upper(), m_data.group(2).upper())
                    data_pendente = (m_data.group(1), mes_raw)
                    continue

            # Resolve detalhes do Fallback
            m_det = RE_DETALHE.search(texto)
            if m_det:
                cartao    = m_det.group(1)
                desc_raw  = m_det.group(2).strip()
                valor_str = m_det.group(3)

                parcela = None
                m_parc = RE_PARCELA.search(desc_raw)
                if m_parc:
                    parcela  = m_parc.group(1)
                    desc_raw = RE_PARCELA.sub("", desc_raw).strip()

                if data_pendente:
                    dia, mes = data_pendente
                    ano      = inferir_ano(mes, vcto_ano, vcto_mes)
                    mes_num  = MESES_PT.get(mes, "01")
                    data_iso = f"{ano}-{mes_num}-{dia}"
                    data_pendente = None
                else:
                    data_iso = (
                        transacoes[-1]["data"] if transacoes else f"{vcto_ano}-{vcto_mes:02d}-01"
                    )

                transacoes.append({
                    "data":         data_iso,
                    "cartao_final": cartao,
                    "descricao":    desc_raw,
                    "parcela":      parcela,
                    "valor":        valor_float(valor_str),
                })

    return transacoes


def processar_fatura(converter: DocumentConverter, pdf_stream: io.BytesIO, filename: str = "fatura.pdf") -> dict:
    print(f"📄 Lendo PDF via DocumentConverter (Export Markdown): {filename}")
    paginas = extrair_paginas_texto(converter,pdf_stream, filename)

    print("🔍 Extraindo metadados...")
    meta = extrair_metadados(paginas)

    print("💳 Extraindo transações...")
    transacoes = extrair_transacoes(paginas, meta)

    return {
        "fatura": {
            "titular":        meta.get("titular"),
            "vencimento":     meta.get("vencimento"),
            "total_fatura":   meta.get("total_fatura"),
            "periodo_inicio": meta.get("periodo_inicio"),
            "periodo_fim":    meta.get("periodo_fim"),
        },
        "total_transacoes": len(transacoes),
        "soma_compras":     round(sum(t["valor"] for t in transacoes), 2),
        "transacoes":       transacoes,
    }