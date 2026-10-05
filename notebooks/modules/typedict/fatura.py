from typing import TypedDict, List, Optional

# 1. Definimos os sub-níveis
class FaturaInfo(TypedDict):
    titular: str
    vencimento: str
    total_fatura: float
    periodo_inicio: str
    periodo_fim: str

class Transacao(TypedDict):
    data: str
    cartao_final: str
    descricao: str
    parcela: Optional[str] # Para aceitar None
    valor: float

# 2. Definimos a estrutura principal
class FaturaDict(TypedDict):
    fatura: FaturaInfo
    total_transacoes: int
    soma_compras: float
    transacoes: List[Transacao]