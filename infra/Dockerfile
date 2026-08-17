FROM python:3.9-slim
# Instala o driver do Kafka para Python
RUN pip install kafka-python==2.0.2
# Copia o seu script
COPY scripts/init.py /scripts/init.py

# Define o comando padrão
CMD ["python", "init.py"]