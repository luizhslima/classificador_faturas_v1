from minio import Minio
from minio.error import S3Error


def conectar_minio(
    endpoint="192.168.15.18:9000",
    access_key="admin_tcc",
    secret_key="senha_super_segura",
    secure=False,
):
    """
    Cria e retorna um cliente conectado ao MinIO.

    :param endpoint: host:porta do servidor MinIO (sem http/https)
    :param access_key: chave de acesso
    :param secret_key: chave secreta
    :param secure: True para HTTPS, False para HTTP
    :return: instância de Minio ou None em caso de erro
    """
    try:
        client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        # Testa a conexão listando os buckets
        client.list_buckets()
        print("Conexão com MinIO estabelecida com sucesso!")
        return client
    except S3Error as e:
        print(f"Erro ao conectar no MinIO: {e}")
        return None