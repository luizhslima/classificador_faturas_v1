from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer
from langchain_postgres.vectorstores import PGVector

class STEmbeddings(Embeddings):
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.model.encode(text).tolist()


class PostgresService:
    
    COLLECTION_NAME = "baseconhecimento"
    SIMILARITY_THRESHOLD = 0.85

    def __init__(self, db_url: str,model_name:str = "paraphrase-multilingual-MiniLM-L12-v2") -> None:
            engine = create_engine(db_url)
            self.session_factory = sessionmaker(engine, expire_on_commit=False,autocommit=False,autoflush=False)
            self.embeddings = STEmbeddings(model_name=model_name)
        
    
            self.vectorstore = PGVector(
                        embeddings=self.embeddings,
                        collection_name=self.COLLECTION_NAME,
                        connection=engine,
                        use_jsonb=True,
                        async_mode=True)
        