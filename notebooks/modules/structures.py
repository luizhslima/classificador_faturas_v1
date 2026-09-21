from pydantic import BaseModel, Field


class ClassificacaoLLM(BaseModel):
    categoria: str = Field(
        description="Categoria principal sugerida para a transação."
    )
    subcategoria: str | None = Field(
        default=None,
        description="Subcategoria sugerida, caso seja possível identificar.",
    )
    confianca: float = Field(
        ge=0.0,
        le=1.0,
        description="Confiança da classificação, entre 0 e 1.",
    )
    justificativa: str = Field(
        description="Justificativa curta baseada exclusivamente no nome da transação."
    )
    requer_confirmacao: bool = Field(
        description="True quando a evidência for insuficiente ou houver ambiguidade."
    )
    possiveis_categorias: list[str] = Field(
        default=[],
        description="Lista de pelo menos três categorias alternativas possíveis para a transação."
    )
    raciocinio: str = Field(
        description="Raciocínio usado para categorizar a transação."
    )