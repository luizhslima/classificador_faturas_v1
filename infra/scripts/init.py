import os
import time
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import NoBrokersAvailable, NodeNotReadyError

def init_kafka_topics():
    # 1. Lê as variáveis de ambiente passadas pelo Docker Compose
    bootstrap_servers = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    topics_env = os.environ.get('KAFKA_TOPICS', 'datalake-bronze-ingestao-topic')
    
    if not topics_env:
        print("Nenhum tópico configurado na variável KAFKA_TOPICS. Saindo...")
        return

    # Limpa os espaços e cria uma lista de nomes de tópicos
    topic_names = [t.strip() for t in topics_env.split(',')]
    
    print(f"A tentar ligar ao Kafka em: {bootstrap_servers}")
    
    # 2. Loop de tentativas (Retry Pattern)
    # O broker do Kafka pode demorar uns 10-15 segundos a ficar pronto
    admin_client = None
    max_retries = 15
    for attempt in range(1, max_retries + 1):
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=bootstrap_servers,
                client_id='init-topics-script'
            )
            print(f"✅ Ligado ao Kafka com sucesso na tentativa {attempt}!")
            break
        except (NoBrokersAvailable, NodeNotReadyError):
            print(f"⏳ Kafka ainda não está pronto (Tentativa {attempt}/{max_retries}). A aguardar 3 segundos...")
            time.sleep(3)
            
    if not admin_client:
        print("❌ Falha ao contactar o Kafka após várias tentativas. Abortando.")
        exit(1) # Força o restart: on-failure do Docker Compose

    # 3. Verifica os tópicos que já existem
    existing_topics = admin_client.list_topics()
    
    new_topics_to_create = []
    for topic in topic_names:
        if topic not in existing_topics:
            # Configuração padrão para ambiente local (1 partição, 1 réplica)
            new_topics_to_create.append(NewTopic(name=topic, num_partitions=1, replication_factor=1))
        else:
            print(f"🔹 O tópico '{topic}' já existe. Ignorando.")

    # 4. Cria os tópicos em falta
    if new_topics_to_create:
        try:
            admin_client.create_topics(new_topics=new_topics_to_create, validate_only=False)
            criados = [t.name for t in new_topics_to_create]
            print(f"🚀 Tópicos criados com sucesso: {criados}")
        except Exception as e:
            print(f"❌ Erro ao tentar criar os tópicos: {e}")
            exit(1)
    else:
        print("✨ Todos os tópicos já estavam criados. Nenhuma ação necessária.")

    # Fecha a conexão limpa
    admin_client.close()
    print("==========================================")
    print("✅ Inicialização do Kafka concluída!")
    print("==========================================")

if __name__ == '__main__':
    init_kafka_topics()