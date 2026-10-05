from modules.service_ocr import ServiceOCR
from notebooks.modules.sync_service import SyncService
from minio.datatypes import Object
from modules.model import Fatura, Transacao
from decimal import Decimal
from datetime import datetime, date
import io
from modules.parsers import extrair_uuid, normalizar_nome, parse_data_curta, parse_periodo_inteligente
import logging

log = logging.getLogger(__name__)

def fatura_nubank_parser(service: ServiceOCR, io:io.BytesIO, databaseService: SyncService, stats: Object):
    result = service.processar_pdf_nativo(io)
    with databaseService.session_factory() as session:
        try:
           
            venc = datetime.strptime(result.get('fatura').get('vencimento'), "%Y-%m-%d").date()
            p_inicio = parse_periodo_inteligente(result.get('fatura').get('periodo_inicio'), venc)
            p_fim = parse_periodo_inteligente(result.get('fatura').get('periodo_fim'), venc)
            fatura = Fatura(
                            usuario_id=1,
                            referencia=stats.bucket_name,
                            data_inicio=p_inicio,
                            data_fim=p_fim,
                            valor_total=result.get('fatura').get('total_fatura'),
                            arquivo_origem=stats.object_name,
                            status='processando',
                            uuid_fatura=extrair_uuid(stats.object_name)
                        )
            session.add(fatura)
            session.flush()
            
            transacoes = [
                Transacao(
                    fatura_id=fatura.id,
                    nome_original=transacao.get('descricao'),
                    nome_normalizado=normalizar_nome(transacao.get('descricao')),
                    valor=Decimal(transacao.get('valor')),
                    data_transacao=transacao.get('data'),
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
                for transacao in result.get('transacoes')
            ]
            session.add_all(transacoes)
            fatura.status = "concluida"
            log.info(
                    "Fatura salva com sucesso. fatura_id=%s transacoes=%s",
                    fatura.id,
                    len(transacoes),
            )
            session.commit()
        except Exception as e:
            log.error(e)
            session.rollback()