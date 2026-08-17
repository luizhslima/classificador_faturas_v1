from langchain_core.prompts import ChatPromptTemplate

PROMPT = ChatPromptTemplate.from_template("""
Você é um classificador de gastos de cartão de crédito.
Classifique o estabelecimento abaixo em uma categoria financeira.

Estabelecimento: {nome}
Contexto adicional: {contexto}

Responda em JSON: {{"categoria": "...", "confianca": 0.0}}
""")

class QwenLocalProvider:
    def __init__(self, model: str = "qwen/qwen3.5-9b", base_url: str = "http://127.0.0.1:1234/v1"):
        pass