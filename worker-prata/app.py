import json
import logging
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from kafka.consumer.subscription_state import ConsumerRebalanceListener
from minio import Minio
from modules.minioconfig import conectar_minio
from modules.parsers import save_csv_nubank
from modules.bitparser import fatura_nubank_parser
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
DATABASE_URL="postgresql+psycopg2://n8n:n8n_dev_password@192.168.15.18:5433/agent"


class RebalanceListener(ConsumerRebalanceListener):
    def on_partitions_assigned(self, assigned):
        logging.info("Partições atribuídas ao consumer: %s", assigned)

    def on_partitions_revoked(self, revoked):
        logging.info("Partições revogadas do consumer: %s", revoked)

def connect_broker(s3Client:Minio):
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


                    stat = s3Client.stat_object('bronze-raw', value['caminhoMinio'])

                    if stat.content_type not in ("text/csv", "application/pdf"):
                        log.warning("Formato não suportado: %s", stat.content_type)
                        continue
                    response = s3Client.get_object('bronze-raw',value['caminhoMinio'])
                    try:
                        if stat.content_type == "text/csv":
                           save_csv_nubank(BytesIO(response.read()), service, stat)

                        if stat.content_type == "application/pdf":
                            serviceOCR = ServiceRapidOCR()
                            fatura_nubank_parser(serviceOCR, BytesIO(response.read()), service, stat)
                    finally:
                        response.close()
                        response.release_conn()
    except KeyboardInterrupt:
        log.info("Encerrando consumer...")
    finally:
        consumer.close()
        log.info("Consumer encerrado.")

def app():
    s3Client: Minio |  None = conectar_minio()
    if s3Client is None:
       raise ValueError("Nao foi posivel conectar no S3/Minio")
    connect_broker(s3Client)


if __name__ == "__main__":
    app()

#docker exec -it kafka  /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic datalake-bronze-ingestao-topic

#docker exec -it kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group datalake-worker-group


#docker exec -it kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list | grep __consumer_offsets