from io import BytesIO
import pandas as pd
from modules.model import Fatura, Transacao
from modules.service import Service
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


def save_csv_nubank(byte: BytesIO, service: Service, stats: Object):
    

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