import re
import io
import warnings
from datetime import datetime, timedelta
from typing import cast, Union, Optional
from pathlib import Path

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import DocumentStream

try:
    from typedict.fatura import FaturaDict, Transacao
except ModuleNotFoundError:
    from modules.typedict.fatura import FaturaDict, Transacao


warnings.filterwarnings("ignore")

# ─── Constantes e Ajustes para OCR ────────────────────────────────────────────

MESES_PT = {
    "JAN": "01", "FEV": "02", "MAR": "03", "ABR": "04",
    "MAI": "05", "JUN": "06", "JUL": "07", "AGO": "08",
    "SET": "09", "OUT": "10", "NOV": "11", "DEZ": "12",
}

MESES_EXTENSO = {
    "JANEIRO": "01", "FEVEREIRO": "02", "MARÇO": "03", "MARCO": "03",
    "ABRIL": "04", "MAIO": "05", "JUNHO": "06", "JULHO": "07",
    "AGOSTO": "08", "SETEMBRO": "09", "OUTUBRO": "10", "NOVEMBRO": "11",
    "DEZEMBRO": "12",
}

OCR_MESES_CORRECAO = {
    "MAL": "MAI", "MAl": "MAI", "MA1": "MAI",
    "JUI": "JUL", "JU1": "JUL",
    "ABP": "ABR", "0UT": "OUT", "OUT": "OUT",
}

# Regex para Metadados e Transações
RE_DATA = re.compile(r"^(\d{2})\s+([A-Za-z]{3})$")
RE_PARCELA = re.compile(r"\s*(?:-\s*)?Parcela\s+(\d+/\d+)", re.IGNORECASE)
RE_VALOR = re.compile(r"([\d.]+,\d{2})")
RE_FINAL_CARTAO = re.compile(r"Final\s+(\d{4})", re.IGNORECASE)


def valor_float(s: str) -> float:
    """Converte valor monetário brasileiro (ex: '1.770,42') para float (1770.42)."""
    return float(s.replace(".", "").replace(",", "."))


def inferir_ano(mes_str: str, vcto_ano: int, vcto_mes: int) -> int:
    """Infere o ano da transação caso pertença ao ciclo do ano anterior."""
    mes_num = int(MESES_PT.get(mes_str.upper(), "01"))
    return vcto_ano - 1 if mes_num > vcto_mes else vcto_ano


def extrair_paginas_texto(
    converter: DocumentConverter,
    pdf_stream: Union[io.BytesIO, bytes, str, Path],
    filename: str = "fatura.pdf",
) -> dict[int, list[tuple[float, str]]]:
    """
    Exporta o documento para Markdown via Docling, preservando o layout
    de tabelas estruturadas e fluxo contínuo de texto.
    """
    if isinstance(pdf_stream, (str, Path)):
        conv = converter.convert(str(pdf_stream))
    elif isinstance(pdf_stream, bytes):
        conv = converter.convert(DocumentStream(name=filename, stream=io.BytesIO(pdf_stream)))
    else:
        conv = converter.convert(DocumentStream(name=filename, stream=pdf_stream))

    doc = conv.document
    texto_md = doc.export_to_markdown()

    # Normaliza em uma lista indexada para leitura sequencial Top-Down
    paginas = {1: []}
    for y_dummy, linha in enumerate(texto_md.split("\n")):
        linha_limpa = linha.strip()
        if linha_limpa:
            paginas[1].append((float(y_dummy), linha_limpa))

    return paginas


def extrair_metadados(paginas: dict) -> dict:
    """Extrai cabeçalho e metadados gerais da fatura do C6 Bank."""
    texto_total = "\n".join(t for linhas in paginas.values() for _, t in linhas)
    meta = {}

    # 1. Titular
    m = re.search(r"([A-ZÀ-ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-ÿ][a-zà-ÿ]+)+)\s+Cartão C6", texto_total)
    if m:
        meta["titular"] = m.group(1).strip()
    else:
        m = re.search(r"Olá,\s*([A-Za-zÀ-ÿ]+)", texto_total)
        if m:
            meta["titular"] = m.group(1).strip()

    # 2. Total da Fatura
    m = re.search(r"(?:chegou no valor de|Valor da fatura:)\s*R\$\s*([\d.,]+)", texto_total)
    if m:
        meta["total_fatura"] = valor_float(m.group(1))
    else:
        m = re.search(r"Total a pagar\s*\n+\s*R\$\s*([\d.,]+)", texto_total)
        if m:
            meta["total_fatura"] = valor_float(m.group(1))

    # 3. Vencimento
    m = re.search(r"Vencimento:?\s*(?:R\$\s*[\d.,]+\s*)?(\d{2})/(\d{2})/(\d{4})", texto_total, re.IGNORECASE)
    if m:
        dia, mes, ano = m.group(1), m.group(2), m.group(3)
        meta["vencimento"] = f"{ano}-{mes}-{dia}"
        meta["_vcto_ano"]  = int(ano)
        meta["_vcto_mes"]  = int(mes)
    else:
        m2 = re.search(r"(?:Data do vencimento|Vencimento):\s*(\d{2})\s+de\s+([A-Za-zÀ-ÿ]+)", texto_total, re.IGNORECASE)
        if m2:
            dia = m2.group(1)
            mes_ext = m2.group(2).upper()
            mes_num = MESES_EXTENSO.get(mes_ext, "01")
            ano_corrente = datetime.now().year
            meta["vencimento"] = f"{ano_corrente}-{mes_num}-{dia}"
            meta["_vcto_ano"]  = ano_corrente
            meta["_vcto_mes"]  = int(mes_num)

    # 4. Período / Fechamento
    m = re.search(r"fechamento desta fatura em\s*(\d{2})/(\d{2})/(\d{2,4})", texto_total, re.IGNORECASE)
    if m:
        dia_f, mes_f, ano_f = m.group(1), m.group(2), m.group(3)
        if len(ano_f) == 2:
            ano_f = f"20{ano_f}"
        data_fim = datetime(int(ano_f), int(mes_f), int(dia_f))
        data_ini = data_fim - timedelta(days=29)
        meta["periodo_fim"]    = data_fim.strftime("%d/%m/%Y")
        meta["periodo_inicio"] = data_ini.strftime("%d/%m/%Y")

    return meta


def extrair_transacoes(paginas: dict, meta: dict) -> list[Transacao]:
    """
    Extrai as transações dos cartões (principal, adicionais e virtuais)
    presentes na fatura do C6 Bank.
    """
    vcto_ano = meta.get("_vcto_ano", datetime.now().year)
    vcto_mes = meta.get("_vcto_mes", datetime.now().month)

    transacoes: list[Transacao] = []
    linhas = [t for _, t in paginas.get(1, [])]

    dentro_secao = False
    cartao_atual = ""

    i = 0
    while i < len(linhas):
        linha = linhas[i]

        # ── Detecta início da seção de compras ────────────────────────────
        if "TRANSAÇÕES DO CARTÃO" in linha.upper() or "TRANSACOES DO CARTAO" in linha.upper():
            dentro_secao = True
            i += 1
            continue

        if not dentro_secao:
            i += 1
            continue

        # ── Detecta fim da seção de transações ───────────────────────────
        if any(term in linha.upper() for term in ["FORMAS DE PAGAMENTO", "RECIBO DO PAGADOR", "FICHA DE COMPENSAÇÃO"]):
            dentro_secao = False
            break

        # ── Identificação / Troca de Cartão (Físico / Virtual) ───────────
        m_card = RE_FINAL_CARTAO.search(linha)
        if m_card and any(k in linha.upper() for k in ["C6", "CARTÃO", "CARTAO", "SUBTOTAL"]):
            cartao_atual = m_card.group(1)

        # ── Tentativa 1: Linha de Tabela Markdown (| ... | ... |) ─────────
        if linha.startswith("|") and linha.endswith("|"):
            # Ignora linhas divisórias (|---|)
            if set(linha.replace("|", "").strip()) <= {"-", ":", " "}:
                i += 1
                continue

            if m_card:
                cartao_atual = m_card.group(1)
                i += 1
                continue

            cols = [c.strip() for c in linha.split("|")[1:-1]]
            # Remove eventuais colunas vazias iniciais geradas por ícones/checkbox
            while cols and not cols[0]:
                cols.pop(0)

            if cols:
                m_dt = RE_DATA.match(cols[0])
                if m_dt:
                    dia = m_dt.group(1)
                    mes_raw = m_dt.group(2).upper()
                    mes_corrigido = OCR_MESES_CORRECAO.get(mes_raw, mes_raw)

                    # Valor normalmente está na última coluna
                    vals = RE_VALOR.findall(cols[-1])
                    if vals:
                        v_str = vals[-1]
                        desc = cols[1] if len(cols) > 2 else ""
                        if not desc and len(cols) == 2:
                            desc = cols[1]

                        # Limpa pipes residuais na descrição
                        desc = desc.replace("|", "").strip()

                        # Identifica e extrai parcela
                        parcela: Optional[str] = None
                        m_parc = RE_PARCELA.search(desc)
                        if m_parc:
                            parcela = m_parc.group(1)
                            desc = RE_PARCELA.sub("", desc).strip()

                        # Ignora pagamentos de faturas anteriores
                        if any(p in desc.upper() for p in ["INCLUSAO DE PAGAMENTO", "INCLUSÃO DE PAGAMENTO", "PAGAMENTO RECEBIDO"]):
                            i += 1
                            continue

                        val = valor_float(v_str)
                        if "ESTORNO" in desc.upper() or (len(cols) > 2 and "ESTORNO" in cols[2].upper()):
                            val = -abs(val)

                        ano = inferir_ano(mes_corrigido, vcto_ano, vcto_mes)
                        mes_num = MESES_PT.get(mes_corrigido, "01")

                        transacoes.append({
                            "data":         f"{ano}-{mes_num}-{dia}",
                            "cartao_final": cartao_atual,
                            "descricao":    desc,
                            "parcela":      parcela,
                            "valor":        val,
                        })
                        i += 1
                        continue

        # ── Tentativa 2: Linhas Sequenciais / Parágrafos ──────────────────
        m_dt = RE_DATA.match(linha)
        if m_dt:
            dia = m_dt.group(1)
            mes_raw = m_dt.group(2).upper()
            mes_corrigido = OCR_MESES_CORRECAO.get(mes_raw, mes_raw)

            j = i + 1
            desc_lines = []
            val_found = None

            while j < len(linhas) and j < i + 6:
                prox = linhas[j]
                if RE_DATA.match(prox) or RE_FINAL_CARTAO.search(prox) or "TRANSAÇÕES DO CARTÃO" in prox.upper():
                    break
                m_v = re.match(r"^\s*([\d.]+,\d{2})\s*$", prox)
                if m_v:
                    val_found = m_v.group(1)
                    j += 1
                    break
                else:
                    desc_lines.append(prox)
                j += 1

            if val_found:
                desc = " ".join(desc_lines).strip()
                parcela = None
                m_parc = RE_PARCELA.search(desc)
                if m_parc:
                    parcela = m_parc.group(1)
                    desc = RE_PARCELA.sub("", desc).strip()

                if any(p in desc.upper() for p in ["INCLUSAO DE PAGAMENTO", "INCLUSÃO DE PAGAMENTO", "PAGAMENTO RECEBIDO"]):
                    i = j
                    continue

                val = valor_float(val_found)
                if "ESTORNO" in desc.upper():
                    val = -abs(val)

                ano = inferir_ano(mes_corrigido, vcto_ano, vcto_mes)
                mes_num = MESES_PT.get(mes_corrigido, "01")

                transacoes.append({
                    "data":         f"{ano}-{mes_num}-{dia}",
                    "cartao_final": cartao_atual,
                    "descricao":    desc,
                    "parcela":      parcela,
                    "valor":        val,
                })
                i = j
                continue

        i += 1

    return transacoes


def processar_fatura_nativo(
    converter: DocumentConverter,
    pdf_stream: Union[io.BytesIO, bytes, str, Path],
    filename: str = "fatura.pdf",
) -> FaturaDict:
    """
    Processa uma fatura PDF do C6 Bank via Docling DocumentConverter,
    extraindo metadados, identificando múltiplos cartões e retornando
    um FaturaDict estruturado.
    """
    print(f"📄 Lendo PDF C6 Bank via DocumentConverter (Export Markdown): {filename}")
    paginas = extrair_paginas_texto(converter, pdf_stream, filename)

    print("🔍 Extraindo metadados...")
    meta = extrair_metadados(paginas)

    print("💳 Extraindo transações...")
    transacoes = extrair_transacoes(paginas, meta)

    return {
        "fatura": {
            "titular":        cast(str,   meta.get("titular")),
            "vencimento":     cast(str,   meta.get("vencimento")),
            "total_fatura":   cast(float, meta.get("total_fatura")),
            "periodo_inicio": cast(str,   meta.get("periodo_inicio")),
            "periodo_fim":    cast(str,   meta.get("periodo_fim")),
        },
        "total_transacoes": len(transacoes),
        "soma_compras":     round(sum(t["valor"] for t in transacoes), 2),
        "transacoes":       transacoes,
    }


# Aliases para compatibilidade de importação
processar_fatura = processar_fatura_nativo
processar_fatura_nativo_c6 = processar_fatura_nativo
