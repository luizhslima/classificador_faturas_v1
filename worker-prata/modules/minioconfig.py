import os
import logging
from io import BytesIO
from typing import Optional, BinaryIO
from contextlib import contextmanager
from minio import Minio
from minio.error import S3Error
from minio.datatypes import Object

log = logging.getLogger(__name__)


class MinioConnection:
    """
    Classe responsável por gerenciar a conexão e operações com o MinIO / S3.
    
    Permite configuração via parâmetros ou variáveis de ambiente:
    - MINIO_ENDPOINT (padrão: "192.168.15.18:9000")
    - MINIO_ACCESS_KEY (obrigatória, sem valor padrão)
    - MINIO_SECRET_KEY (obrigatória, sem valor padrão)
    - MINIO_SECURE (padrão: False)
    """

    def __init__(
        self,
        endpoint: str = "192.168.15.18:9000",
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        secure: bool = False,
        auto_connect: bool = True,
    ):
        self.endpoint = os.getenv("MINIO_ENDPOINT", endpoint)
        self.access_key = os.getenv("MINIO_ACCESS_KEY", access_key)
        self.secret_key = os.getenv("MINIO_SECRET_KEY", secret_key)
        if not self.access_key or not self.secret_key:
            raise ValueError("Defina MINIO_ACCESS_KEY e MINIO_SECRET_KEY no ambiente (ver .env.example).")
        
        env_secure = os.getenv("MINIO_SECURE")
        if env_secure is not None:
            self.secure = env_secure.lower() in ("true", "1", "yes")
        else:
            self.secure = secure

        self._client: Optional[Minio] = None

        if auto_connect:
            self.connect()

    def connect(self) -> Minio:
        """
        Cria e valida a conexão com o servidor MinIO.
        """
        try:
            log.info("Conectando ao MinIO em %s (secure=%s)...", self.endpoint, self.secure)
            self._client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )
            # Valida conectividade listando buckets
            self._client.list_buckets()
            log.info("Conexão com MinIO estabelecida com sucesso!")
            return self._client
        except S3Error as e:
            log.error("Erro S3 ao conectar no MinIO: %s", e)
            raise
        except Exception as e:
            log.error("Erro inesperado ao conectar no MinIO: %s", e)
            raise

    @property
    def client(self) -> Minio:
        """
        Retorna o cliente MinIO nativo. Inicializa a conexão se necessário.
        """
        if self._client is None:
            self.connect()
        return self._client

    def stat_object(self, bucket_name: str, object_name: str) -> Object:
        """
        Obtém os metadados de um objeto no bucket (content_type, tamanho, etc).
        """
        try:
            return self.client.stat_object(bucket_name=bucket_name, object_name=object_name)
        except S3Error as e:
            log.error("Erro ao obter stat de '%s/%s': %s", bucket_name, object_name, e)
            raise

    @contextmanager
    def get_object_stream(self, bucket_name: str, object_name: str):
        """
        Context manager para leitura de stream de um objeto com liberação automática de conexões.
        
        Exemplo:
            with minio_conn.get_object_stream("bucket", "arquivo.pdf") as response:
                dados = response.read()
        """
        response = None
        try:
            response = self.client.get_object(bucket_name=bucket_name, object_name=object_name)
            yield response
        except S3Error as e:
            log.error("Erro ao obter objeto '%s/%s': %s", bucket_name, object_name, e)
            raise
        finally:
            if response is not None:
                response.close()
                response.release_conn()

    def get_object_bytes(self, bucket_name: str, object_name: str) -> bytes:
        """
        Lê e retorna todo o conteúdo binário de um objeto.
        """
        with self.get_object_stream(bucket_name, object_name) as response:
            return response.read()

    def get_object_bytes_io(self, bucket_name: str, object_name: str) -> BytesIO:
        """
        Lê o objeto e o retorna encapsulado em uma instância de io.BytesIO.
        """
        return BytesIO(self.get_object_bytes(bucket_name, object_name))

    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: BinaryIO | BytesIO,
        length: int,
        content_type: str = "application/octet-stream",
    ):
        """
        Faz upload de um objeto para o MinIO.
        """
        try:
            return self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=data,
                length=length,
                content_type=content_type,
            )
        except S3Error as e:
            log.error("Erro ao enviar objeto para '%s/%s': %s", bucket_name, object_name, e)
            raise

    def bucket_exists(self, bucket_name: str) -> bool:
        """
        Verifica se um determinado bucket existe.
        """
        try:
            return self.client.bucket_exists(bucket_name)
        except S3Error as e:
            log.error("Erro ao verificar existência do bucket '%s': %s", bucket_name, e)
            return False

    def list_buckets(self):
        """
        Lista todos os buckets disponíveis.
        """
        try:
            return self.client.list_buckets()
        except S3Error as e:
            log.error("Erro ao listar buckets: %s", e)
            raise


def conectar_minio(
    endpoint: str = "192.168.15.18:9000",
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    secure: bool = False,
) -> Optional[Minio]:
    """
    Função utilitária legada para manter compatibilidade retroativa.
    Cria e retorna a instância direta do cliente MinIO ou None em caso de erro.
    """
    try:
        conn = MinioConnection(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        return conn.client
    except Exception as e:
        log.error("Erro ao conectar no MinIO via conectar_minio: %s", e)
        return None