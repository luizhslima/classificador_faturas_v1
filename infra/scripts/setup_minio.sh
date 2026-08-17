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

yt-dlp https://www.erome.com/a/apURE5dh & yt-dlp https://www.erome.com/a/3NTv0Y6E & yt-dlp https://www.erome.com/a/jrQroqwm & yt-dlp https://www.erome.com/a/Oc9zS64B & yt-dlp https://www.erome.com/a/QQ8TAif6 & yt-dlp https://www.erome.com/a/I3vEmi1X & yt-dlp https://www.erome.com/a/BMzyfKvD & yt-dlp https://www.erome.com/a/Hg6pD7bD