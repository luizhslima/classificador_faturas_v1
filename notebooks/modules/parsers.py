from io import BytesIO
import pandas as pd
from modules.model import Fatura, Transacao
from modules.sync_service import SyncService
from minio.datatypes import Object
from price_parser import Price
import re
import logging
from pathlib import PurePosixPath
import uuid
from decimal import Decimal
from datetime import datetime, date

log = logging.getLogger(__name__)



MESES_PT = {
    "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12
}

def parse_data_curta(data_str: str, ano: int) -> date:
    """Converte '01 MAI' para date(ano, 5, 1)"""
    try:
        dia, mes_nome = data_str.strip().split()
        mes = MESES_PT[mes_nome.upper()]
        return date(ano, mes, int(dia))
    except (ValueError, KeyError):
        raise ValueError("data incorreta")


def get_data(datestr: str):
    data_vencimento = datetime.strptime(datestr, "%Y-%m-%d").date()
    ano_fatura = data_vencimento.year
    return (data_vencimento, ano_fatura)

def parse_periodo_inteligente(data_str: str, data_referencia: date) -> date:
    dia, mes_nome = data_str.strip().split()
    mes = MESES_PT[mes_nome.upper()]
    
    # Tenta primeiro o ano da referência (ex: 2026)
    data_tentativa = date(data_referencia.year, mes, int(dia))
    
    # Se a data de início for depois do vencimento, 
    # significa que ela provavelmente é do ano anterior
    if data_tentativa > data_referencia:
        return data_tentativa.replace(year=data_referencia.year - 1)
    
    return data_tentativa

def extrair_uuid(object_name: str | None) -> str | None:
    if object_name is None:
        log.error("object_name está None")
        return None

    possivel_uuid = PurePosixPath(object_name).parent.name

    try:
        uuid.UUID(possivel_uuid)
        return possivel_uuid
    except ValueError:
        log.error("UUID não encontrado no caminho: %s", object_name)
        return None

def normalizar_nome(nome: str) -> str:
    texto = nome.lower()

    texto = re.sub(r"\b(pag|pix|compra|debito|credito)\b\*?", "", texto)
    texto = re.sub(r"\b(ltda|me|epp|sa|s/a|eireli)\b", " ", texto)

    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\b\d{4,}\b", " ", texto)

    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def save_csv_nubank(byte: BytesIO, service: SyncService, stats: Object):
    

    with service.session_factory() as session:
        try:
            df = pd.read_csv(byte)
            df['amount'] = df['amount'].apply(lambda x: Price.fromstring(x).amount_float)
            df = df[df['title'].str.lower().str.strip() != 'pagamento recebido']
            df_limpo = df[df['amount'] > 0]
            fatura = Fatura(
                usuario_id=1,
                referencia=stats.bucket_name,
                data_inicio=min(df['date']),
                data_fim=max(df['date']),
                valor_total=Decimal(df_limpo['amount'].sum()).quantize(Decimal("0.01")),
                arquivo_origem=stats.object_name,
                status='processando',
                uuid_fatura=extrair_uuid(stats.object_name)
            )
            session.add(fatura)
            session.flush()
            trancacoes = [
                    Transacao(
                        fatura_id=fatura.id,
                        nome_original=row['title'],
                        nome_normalizado=normalizar_nome(row['title']),
                        valor=Decimal(row['amount']),
                        data_transacao=row['date'],
                        categoria_id=None,
                        subcategoria_id=None,
                        estabelecimento_id=None,
                        confianca=None,
                        metodo_classificacao=None,
                        categoria_sugerida_id=None,
                        subcategoria_sugerida_id=None,
                        confianca_sugestao=None,
                        origem_detalhamento=None,
            
                        requer_confirmacao=False,
                        status_classificacao="pendente",
                        revisado_usuario=False,
                    )
                    for _,row in df_limpo.iterrows()
                ]
            session.add_all(trancacoes)
            fatura.status = "concluida"
            session.commit()
            log.info(
                "Fatura salva com sucesso. fatura_id=%s transacoes=%s",
                fatura.id,
                len(trancacoes),
            )
        except Exception as e:
            session.rollback()
            log.error(e)
        finally:
            session.close()



def save_c6(byte: BytesIO, service: SyncService, stats: Object):
    with service.session_factory() as session:
        try:
            if isinstance(byte, pd.DataFrame):
                df = byte.copy()
            else:
                try:
                    df = pd.read_csv(byte, sep=';')
                    if len(df.columns) <= 1:
                        if hasattr(byte, 'seek'):
                            byte.seek(0)
                        df = pd.read_csv(byte, sep=',')
                except Exception:
                    if hasattr(byte, 'seek'):
                        byte.seek(0)
                    df = pd.read_csv(byte)

            df.columns = [c.strip() for c in df.columns]

            col_data = next((c for c in df.columns if 'data' in c.lower()), 'Data de Compra')
            col_desc = next((c for c in df.columns if 'descri' in c.lower()), 'Descrição')
            col_valor = next((c for c in df.columns if 'valor' in c.lower() and 'r$' in c.lower()), 'Valor (em R$)')
            col_parcela = next((c for c in df.columns if 'parcela' in c.lower()), 'Parcela')

            def _parse_valor(val):
                if pd.isna(val):
                    return 0.0
                if isinstance(val, (int, float)):
                    return float(val)
                val_str = str(val).strip()
                is_neg = '-' in val_str
                parsed = Price.fromstring(val_str)
                amt = parsed.amount_float if (parsed and parsed.amount_float is not None) else 0.0
                return -amt if is_neg else amt

            df['amount'] = df[col_valor].apply(_parse_valor)

            desc_series = df[col_desc].astype(str).str.lower().str.strip()
            df = df[~desc_series.str.contains('inclusao de pagamento|inclusão de pagamento|pagamento recebido', regex=True, na=False)]
            df_limpo = df[df['amount'] > 0].copy()

            df_limpo['data_transacao'] = pd.to_datetime(df_limpo[col_data], dayfirst=True, errors='coerce').dt.date
            df_limpo = df_limpo.dropna(subset=['data_transacao'])

            all_dates = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce').dt.date.dropna()
            data_inicio = min(all_dates) if not all_dates.empty else (min(df_limpo['data_transacao']) if not df_limpo.empty else None)
            data_fim = max(all_dates) if not all_dates.empty else (max(df_limpo['data_transacao']) if not df_limpo.empty else None)

            def _extrair_nome(row):
                desc = str(row[col_desc]).strip()
                if col_parcela in row and pd.notna(row[col_parcela]):
                    parc = str(row[col_parcela]).strip()
                    if parc and parc.lower() not in ('única', 'unica', '-', ''):
                        if f"parcela {parc}".lower() not in desc.lower():
                            return f"{desc} - Parcela {parc}"
                return desc

            fatura = Fatura(
                usuario_id=1,
                referencia=stats.bucket_name,
                data_inicio=data_inicio,
                data_fim=data_fim,
                valor_total=Decimal(str(round(df_limpo['amount'].sum(), 2))).quantize(Decimal("0.01")),
                arquivo_origem=stats.object_name,
                status='processando',
                uuid_fatura=extrair_uuid(stats.object_name)
            )
            session.add(fatura)
            session.flush()

            trancacoes = [
                Transacao(
                    fatura_id=fatura.id,
                    nome_original=_extrair_nome(row),
                    nome_normalizado=normalizar_nome(_extrair_nome(row)),
                    valor=Decimal(str(round(row['amount'], 2))),
                    data_transacao=row['data_transacao'],
                    categoria_id=None,
                    subcategoria_id=None,
                    estabelecimento_id=None,
                    confianca=None,
                    metodo_classificacao=None,
                    categoria_sugerida_id=None,
                    subcategoria_sugerida_id=None,
                    confianca_sugestao=None,
                    origem_detalhamento=None,
                    requer_confirmacao=False,
                    status_classificacao="pendente",
                    revisado_usuario=False,
                )
                for _, row in df_limpo.iterrows()
            ]
            session.add_all(trancacoes)
            fatura.status = "concluida"
            session.commit()
            log.info(
                "Fatura salva com sucesso. fatura_id=%s transacoes=%s",
                fatura.id,
                len(trancacoes),
            )
        except Exception as e:
            session.rollback()
            log.error(e)
        finally:
            session.close()


save_c6_bank = save_c6