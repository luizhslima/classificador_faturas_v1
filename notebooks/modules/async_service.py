from langchain.chat_models import init_chat_model

from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer
from langchain_postgres.vectorstores import PGVector
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from langgraph.prebuilt import ToolNode
from langchain_community.tools import DuckDuckGoSearchRun, BaseTool

class STEmbeddings(Embeddings):
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.model.encode(text).tolist()


class AsyncService:
    
    COLLECTION_NAME = "baseconhecimento"
    SIMILARITY_THRESHOLD = 0.85

    def __init__(
            self, 
            db_url: str, 
            model_name:str = "paraphrase-multilingual-MiniLM-L12-v2", 
            llm_model: str = "qwen/qwen3.5-9b",
            llm_provider: str = "openai",
            api_key: str | None = None,
            base_url: str | None = None,
            tools: list[BaseTool]  = []
    ) -> None:

        self.tools = tools
        embeddings = STEmbeddings(model_name=model_name)
        
        engine = create_async_engine(db_url)
        self.session_factory = async_sessionmaker(engine, expire_on_commit=False)

        pgvector_url = db_url.replace(
            "postgresql+asyncpg://",
            "postgresql+psycopg://"
        )


        self.vectorstore = PGVector(
            embeddings=embeddings,
            collection_name=self.COLLECTION_NAME,
            connection=pgvector_url,
            use_jsonb=True,
            async_mode=True)
        
        #LLM
        llm_kwargs = {
            "model": llm_model,
            "model_provider": llm_provider,
            "temperature": 0,
            "max_tokens": 2048,
        }



        if api_key:
            llm_kwargs["api_key"] = api_key
        if base_url:
            llm_kwargs["base_url"] = base_url
        
        self.llm = init_chat_model(**llm_kwargs)

        self.retrivier = self.vectorstore.as_retriever(
            search_type='similarity',
            search_kwargs={"k": 3, "score_threshold": 0.85}
        )
        