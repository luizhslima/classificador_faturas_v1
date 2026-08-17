from typing import TypedDict, Optional
from decimal import Decimal


class AlocacaoCategoria(TypedDict, total=False):
    """Representa uma fatia da transação alocada a uma categoria."""
    categoria: str
    subcategoria: Optional[str]
    valor_alocado: Decimal
    percentual_alocado: float
    confianca: float
    fonte: str          # 'usuario', 'nota_fiscal', 'email', 'api_marketplace',
                        # 'historico_usuario', 'llm', 'estimativa'
    confirmado: bool


class SugestaoMarketplace(TypedDict, total=False):
    """Perfil histórico de compras do usuário em um marketplace."""
    categoria: str
    subcategoria: Optional[str]
    quantidade_confirmada: int
    quantidade_sugerida: int
    confianca_historica: float  # 0.0 a 1.0


class AgentState(TypedDict, total=False):

    # ----------------------------------------------------------
    # IDENTIFICAÇÃO
    # ----------------------------------------------------------
    usuario_id: str
    fatura_id: str
    transacao_id: str
    source: str

    # ----------------------------------------------------------
    # DADOS BRUTOS DA TRANSAÇÃO
    # ----------------------------------------------------------
    nome_original: str
    valor: float
    data_transacao: str                 # ISO 8601: 'YYYY-MM-DD'

    # ----------------------------------------------------------
    # NORMALIZAÇÃO
    # ----------------------------------------------------------
    nome_normalizado: str
    estabelecimento_id: Optional[str]
    estabelecimento: str

    # ----------------------------------------------------------
    # TIPO DO ESTABELECIMENTO
    # ----------------------------------------------------------
    tipo_estabelecimento: Optional[str] # 'restaurante', 'marketplace',
                                        # 'streaming', 'farmacia', etc.
    eh_marketplace: bool                # corrigido o typo 'marktplace'

    # ----------------------------------------------------------
    # CLASSIFICAÇÃO PRINCIPAL
    # (para estabelecimentos comuns, é a categoria definitiva)
    # (para marketplaces, representa o canal: 'Marketplace')
    # ----------------------------------------------------------
    categoria: Optional[str]
    subcategoria: Optional[str]
    confianca: float
    fonte: str                          # 'cache', 'vetorial', 'llm', 'manual'
    metodo_classificacao: Optional[str] # 'cache', 'vetorial', 'llm', 'historico_usuario'

    # ----------------------------------------------------------
    # SUGESTÃO DE CATEGORIA DO ITEM (exclusivo para marketplaces)
    # (o que o usuário provavelmente comprou, não o canal)
    # ----------------------------------------------------------
    categoria_sugerida: Optional[str]
    subcategoria_sugerida: Optional[str]
    confianca_sugestao: float
    origem_detalhamento: Optional[str]  # 'fatura', 'historico_usuario',
                                        # 'nota_fiscal', 'email',
                                        # 'api_marketplace', 'estimativa'

    # ----------------------------------------------------------
    # HISTÓRICO DO USUÁRIO NO MARKETPLACE
    # chave: categoria → SugestaoMarketplace
    # ex: {'Eletrônicos': {'quantidade_confirmada': 18, ...}}
    # ----------------------------------------------------------
    historico_marketplace: dict[str, SugestaoMarketplace]

    # ----------------------------------------------------------
    # ALOCAÇÕES MULTICATEGORIA
    # preenchido quando a compra é dividida entre categorias
    # ----------------------------------------------------------
    alocacoes: list[AlocacaoCategoria]
    total_alocado: Decimal              # soma de alocacoes[*].valor_alocado

    # ----------------------------------------------------------
    # CONTROLE DE FLUXO
    # ----------------------------------------------------------
    requer_confirmacao: bool
    status_classificacao: str           # 'pendente', 'classificada', 'sugerida',
                                        # 'confirmada_usuario', 'rejeitada_usuario',
                                        # 'sem_evidencia'
    erro: Optional[str]

    sugestao_categoria: str | None

    justificativa_classificacao: str | None

    possiveis_categorias: list[str] | None

    raciocinio: str | None