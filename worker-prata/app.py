import json
import logging
import os
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from kafka.consumer.subscription_state import ConsumerRebalanceListener
from modules.minioconfig import MinioConnection
from modules.parsers import save_csv_nubank, save_c6_bank
from modules.bitparser import fatura_pdfnativo_parser
from modules.service import Service
from modules.service_ocr import ServiceRapidOCR
from io import BytesIO


# Ativa logs do kafka-python para ver o que está acontecendo
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
log = logging.getLogger(__name__)

BOOTSTRAP_SERVERS = "192.168.15.18:9092"
TOPIC = "datalake-bronze-ingestao-topic"
GROUP_ID = "datalake-worker-group"
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Variável de ambiente DATABASE_URL não definida (ver .env.example).")


class RebalanceListener(ConsumerRebalanceListener):
    def on_partitions_assigned(self, assigned):
        logging.info("Partições atribuídas ao consumer: %s", assigned) 

    def on_partitions_revoked(self, revoked):
        logging.info("Partições revogadas do consumer: %s", revoked)

def connect_broker(minio_conn: MinioConnection):
    log.info(f"Conectando ao broker: {BOOTSTRAP_SERVERS}")
    log.info(f"Tópico: {TOPIC} | Group ID: {GROUP_ID}")
    service = Service(DATABASE_URL)
    try:
        consumer = KafkaConsumer(
            bootstrap_servers=BOOTSTRAP_SERVERS,
            group_id=GROUP_ID,
            auto_offset_reset="latest",     # pega apenas mensagens novas
            enable_auto_commit=True,
            request_timeout_ms=30000,
        )

        consumer.subscribe(["datalake-bronze-ingestao-topic"], listener=RebalanceListener())
    except KafkaError as e:
        log.error(f"Erro ao criar consumer: {e}")
        return

    log.info("Consumer conectado! Aguardando mensagens... (Ctrl+C para sair)")
    log.info(f"Partições atribuídas: {consumer.assignment()}")
    print("-" * 60)

    try:
        while True:
            # poll com timeout de 2s — imprime heartbeat para confirmar que está vivo
            
            records = consumer.poll(timeout_ms=2000)
            #logging.info("Partições atribuídas: %s", consumer.assignment())
            if not records:
                log.debug("Nenhuma mensagem nos últimos 2s... aguardando")
                continue

            for tp, messages in records.items():
                for message in messages:
                    key = message.key.decode("utf-8") if message.key else None
                    try:
                        value = json.loads(message.value.decode("utf-8"))
                    except json.JSONDecodeError:
                        value = message.value.decode("utf-8")

                    print(f"[Partição {message.partition} | Offset {message.offset}]")
                    print(f"  Chave   : {key}")
                    print(f"  Tópico  : {message.topic}")
                    print(f"  Payload : {json.dumps(value, indent=2, ensure_ascii=False)}")
                    print("-" * 60)
                    
                    logging.info(value['idArquivo'])


                    stat = minio_conn.stat_object('bronze-raw', value['caminhoMinio'])

                    if stat.content_type not in ("text/csv", "application/pdf"):
                        log.warning("Formato não suportado: %s", stat.content_type)
                        continue
                    
                    with minio_conn.get_object_stream('bronze-raw', value['caminhoMinio']) as response:
                        file_bytes = BytesIO(response.read())
                        if stat.content_type == "text/csv" and stat.metadata.get('X-Amz-Meta-Source-Context', 'desconhecido') == 'nubank':
                            save_csv_nubank(file_bytes, service, stat)
                                                    
                        if stat.content_type == "text/csv" and stat.metadata.get('X-Amz-Meta-Source-Context', 'desconhecido') == 'c6':
                            save_c6_bank(file_bytes, service, stat)

                        if stat.content_type == "application/pdf":
                            serviceOCR = ServiceRapidOCR()
                            fatura_pdfnativo_parser(serviceOCR, file_bytes, service, stat)
                        
                        
    except KeyboardInterrupt:
        log.info("Encerrando consumer...")
    finally:
        consumer.close()
        log.info("Consumer encerrado.")

def app():
    try:
        minio_conn = MinioConnection()
        connect_broker(minio_conn)
    except Exception as e:
        log.error("Não foi possível conectar ou inicializar o worker: %s", e)
        raise


if __name__ == "__main__":
    app()

#docker exec -it kafka  /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic datalake-bronze-ingestao-topic

#docker exec -it kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group datalake-worker-group


#docker exec -it kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list | grep __consumer_offsets