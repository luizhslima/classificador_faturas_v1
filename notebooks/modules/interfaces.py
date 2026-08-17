from typing import Protocol


class LLMInterface(Protocol):
    async def classificar(self, nome_normalizado: str, contexto: str = "") -> dict:
        """Retorna {'categoria': str, 'confianca': float}"""
        return {}