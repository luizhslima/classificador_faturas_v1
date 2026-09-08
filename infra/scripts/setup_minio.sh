#!/bin/sh

echo "=========================================="
echo "A iniciar a configuração do Data Lakehouse"
echo "=========================================="

echo "A aguardar o arranque do servidor MinIO..."
# Pausa de 5 segundos para garantir que a API S3 está pronta a receber pedidos
sleep 5

# 1. Autenticar o cliente (mc) no servidor MinIO local
echo "A autenticar..."
mc alias set meudatalake http://minio:9000 admin_tcc senha_super_segura

# 2. Criar os buckets com a flag --ignore-existing (não falha se já existirem)
echo "A criar buckets..."
mc mb meudatalake/bronze-raw --ignore-existing
mc mb meudatalake/bronze-txt --ignore-existing
mc mb meudatalake/silver --ignore-existing


echo "=========================================="
echo "Buckets criados e prontos para uso!"
echo "=========================================="

mc mb meudatalake/mlops-dvc --ignore-existing

docker exec -it postgres-n8n pg_dump -U n8n -d agent -F c -f /tmp/agent.dump

docker cp postgres-n8n:/tmp/agent.dump ./agent.dump


scp  luiz@192.168.15.18:/home/luiz/infra-statement-classifier/agent.dump "D:/Luiz Henrique/MBABIGDATA/dbbackups"

