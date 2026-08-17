from sqlalchemy import select
from model import Estabelecimento, SugestaoCategoriaMarketplace, TipoEstabelecimento
from services import Services
from state import AgentState
from utils import normalizar_nome, extrair_metadados_datalake, gerar_regra_ocr
from collections import Counter
from langgraph.types import interrupt
from langsmith import traceable
from structures import ClassificacaoLLM
from langchain_core.messages import HumanMessage, SystemMessage
from decimal import Decimal
from langgraph.types import StreamWriter



MIN_TRANSACOES_HISTORICO = 5
HISTORICO_THRESHOLD = 0.80

# Padrões como aparecem na fatura do cartão
MARKETPLACES_AMBIGUOS: dict[str, list[str]] = {
    "mercado_livre": [
        "MERCADOLIVRE",
        "MERCADO LIVRE",
        "ML*",
        "MELI*",
        "MERCADOPAGO",
        "MERCADO PAGO",
    ],
    "amazon": [
        "AMAZON",
        "AMZN",
        "AMZN MKTPLACE",
        "AMZ*",
        "AMAZON MKTPLACE",
    ],
    "shopee": [
        "SHOPEE",
        "SHOPEE*",
        "SPE*",
    ],
    "magalu": [
        "MAGALU",
        "MAGAZINE LUIZA",
        "MAG*",
        "MAGALUETC",
    ],
    "americanas": [
        "AMERICANAS",
        "LOJAS AMERICANAS",
        "AMER*",
        "B2W",
    ],
    "aliexpress": [
        "ALIEXPRESS",
        "ALI*",
        "ALIBABA",
    ],
    "shein": [
        "SHEIN",
        "SHEIN*",
    ],
    "ifood": [
        "IFOOD",
        "IFOOD*",
        "IF*",
    ],
    "rappi": [
        "RAPPI",
        "RAPPI*",
        "RPP*",
    ],
}

# Set flat para checagem rápida O(1)
_MARKETPLACE_PATTERNS: list[tuple[str, str]] = [
    (marketplace, pattern)
    for marketplace, patterns in MARKETPLACES_AMBIGUOS.items()
    for pattern in patterns
]

def detectar_marketplace(nome_original: str) -> str | None:
    """
    Retorna a chave do marketplace se detectado, ou None.
    Ex: "AMZN MKTPLACE*LIVRO" → "amazon"
    """
    nome_upper = nome_original.upper()

    for marketplace, pattern in _MARKETPLACE_PATTERNS:
        # padrão com wildcard (ex: "ML*")
        if pattern.endswith("*"):
            if nome_upper.startswith(pattern[:-1]):
                return marketplace
        else:
            if pattern in nome_upper:
                return marketplace

    return None




def make_nodes(services: Services):

    async def buscar_estabelecimentos(state: AgentState) -> dict:
        async with services.session_factory() as session:
            result = await session.execute(
                select(Estabelecimento)
                .where(Estabelecimento.nome_normalizado == state.get('nome_normalizado'))
            )
            est = result.scalar_one_or_none()

            if est is None or est.categoria is None:
                return {}

            if est:
                return {
                    "categoria": est.categoria.nome,
                    "confianca": est.confianca,
                    "fonte": "cache_db"
                }
            return {}
        
    async def classificar_com_llm(state: AgentState) -> dict:
        dtlk = extrair_metadados_datalake(state.get('source', ''))
        instrucao_ocr = gerar_regra_ocr(dtlk["is_digital_nativo"])
        async with services.session_factory() as session:
            result = await session.execute(
                select(TipoEstabelecimento)
            )
            tipos = result.scalars().all()
            #prompt = f"Classifique o estabelecimento: {state.get('nome_normalizado')} entre essas categorias: {' '.join([tipo.nome for tipo in tipos])}"
            classificador = services.llm.with_structured_output(
                ClassificacaoLLM
            )
            resposta = await classificador.ainvoke([
                SystemMessage(
                    content=f"""
                            Você é um assistente financeiro especialista em classificar transações de faturas de cartão de crédito no Brasil.
                            CONTEXTO DA EXTRAÇÃO:
                            - Banco Origem: {dtlk.get('source')}
                            - Formato do Dado: {dtlk['extensao']}
                            REGRAS DE ANÁLISE:
                            1. PROCESSADORES DE PAGAMENTO: Prefixos como "PG*", "PAG*", "MP*", "ZOOP*", "SUMUP*" indicam apenas a maquininha/gateway. Descodifique siglas comuns (IFD, UBR, AMZN).
                            2. COMBATE A ALUCINAÇÕES: Não invente marcas ou aplicativos. Se você não reconhecer o estabelecimento com certeza absoluta baseada em fatos reais, não tente forçar um encaixe.
                            3. REGRA DE ORIGEM DO DADO: {instrucao_ocr}
                            4. ESTABELECIMENTOS DESCONHECIDOS: Se a transação for ambígua, um nome próprio informal (ex: 'jhoonymorango'), ou apenas um gateway genérico, defina 'requer_confirmacao=true' e use confiança baixa (<=0.70).
                            5. CADEIA DE PENSAMENTO: Pense passo a passo. Gere o campo "raciocinio" ANTES de gerar a "categoria".
                            CATEGORIAS PERMITIDAS (Você DEVE escolher apenas uma desta lista ):
                            {';'.join([f'Nome:{tipo.nome} - descrição: {tipo.descricao}' for tipo in tipos])}"""
                ),
                HumanMessage(
                    content=(
                        f"Classifique esta transação: {state.get('nome_normalizado')}\n\n"
                        "Retorne a categoria, subcategoria quando possível, "
                        "confiança entre 0 e 1, justificativa curta, "
                        "possíveis categorias alternativas "
                        "e se exige confirmação humana."
                    )
                )
            ])

            return{
                "categoria": resposta.categoria,
                "subcategoria": resposta.subcategoria,
                "confianca": float(str(resposta.confianca)),
                "fonte": "llm",
                "requer_confirmacao": resposta.requer_confirmacao,
                "justificativa_classificacao": resposta.justificativa,
                "possiveis_categorias": resposta.possiveis_categorias,
                "raciocinio": resposta.raciocinio
            }

    @traceable(
            name="Buscar historico de marketplace",
            run_type="retriever"
    )
    async def buscar_historico_marketplace(state: AgentState) -> dict:
        async with services.session_factory() as session:
            result = await session.execute(
                select(SugestaoCategoriaMarketplace)
                .where(
                    SugestaoCategoriaMarketplace.usuario_id ==  state.get('usuario_id'),
                    SugestaoCategoriaMarketplace.quantidade_confirmada > 0
                )
                .order_by(SugestaoCategoriaMarketplace.confianca_historica.desc())
            )
            sugestoes = result.scalars().all()

            historico = {
                s.categoria.nome: {
                    "confirmadas": s.quantidade_confirmada,
                    "confiaca": s.confianca_historica
                }
                for s in sugestoes
            }
            return {"historico_marketplace": historico}
    async def buscar_por_similaridade(state: AgentState):
        docs = await services.retrivier.ainvoke(state.get('nome_normalizado', 'invalido'))

        if not docs:
            return {}

        melhor = docs[0]
        return {
            "categoria": melhor.metadata['categoria'],
            "confianca": float(melhor.metadata['confianca']),
            "fonte": "vetorial",
            "requer_confirmacao": float(melhor.metadata['confianca']) < 0.95,
        }
    async def salvar_no_vectorstore(state: AgentState) -> dict:
        nome = state.get("nome_normalizado")
        if nome is None:
            raise ValueError("nome_normalizado é obrigatório para salvar no vectorstore")

        confianca = state.get("confianca")

        metadata = {
            "categoria": state.get("categoria"),
            "confianca": str(confianca) if confianca is not None else None,
            "fonte": state.get("fonte"),
            "eh_marketplace": state.get("eh_marketplace", False),
        }

        #await services.vectorstore.aadd_texts(
        #    texts=[nome],
        #    metadatas=[metadata],
        #)
        return {}
    def detectar_estabelecimento(nome_normalizado: str) -> str:
        """
        Aqui você pode crescer a lista de aliases conforme aprende.

        Exemplos:
        - AMZN MKTPLACE -> amazon
        - MERCADOLIVRE -> mercado livre
        """
        aliases = {
            "mercado livre": [
                "mercado livre",
                "mercadolivre",
                "mercado pago",
                "mlb",
            ],
            "amazon": [
                "amazon",
                "amzn",
                "amzn mktplace",
            ],
            "shopee": [
                "shopee",
            ],
            "magalu": [
                "magalu",
                "magazine luiza",
            ],
            "americanas": [
                "americanas",
                "americanas com",
            ],
            "aliexpress": [
                "aliexpress",
                "ali express",
            ],
            "shein": [
                "shein",
            ],
        }

        for estabelecimento, nomes in aliases.items():
            if any(alias in nome_normalizado for alias in nomes):
                return estabelecimento

        return nome_normalizado

    def normalizar(state: AgentState) -> AgentState:
        nome = state.get('nome_original');
        if nome is None:
            raise ValueError("nome_normalizado é obrigatório para salvar no vectorstore")
        nome_normalizado = normalizar_nome(nome)
        estabelecimento = detectar_estabelecimento(nome_normalizado)
        state["nome_normalizado"] = nome_normalizado
        state["estabelecimento"] = estabelecimento
        state["eh_marketplace"] = estabelecimento in MARKETPLACES_AMBIGUOS

        return state

    def classificar_marketplace_por_historico(state: AgentState) -> AgentState:
        """AgentState
        Não tenta adivinhar o item comprado apenas pelo valor.

        Se o usuário possui um padrão muito forte para aquele marketplace,
        retorna uma sugestão. Mesmo assim, a confiança é limitada porque
        cada compra pode corresponder a um tipo de produto diferente.
        """
        marketplace = state.get('estabelecimento')
        historico = state.get("historico_marketplaces", {})
        contagens = historico.get(marketplace, {})

        total = sum(contagens.values())

        # Não há histórico suficiente: não inferir categoria de produto.
        if total < MIN_TRANSACOES_HISTORICO:
            state["categoria"] = "Marketplace"
            state["sugestao_categoria"] = None
            state["confianca"] = 1.0
            state["fonte"] = "marketplace_sem_historico"
            state["requer_confirmacao"] = True
            return state

        categoria_mais_frequente, quantidade = Counter(contagens).most_common(1)[0]
        proporcao = quantidade / total

        # Histórico concentrado: sugestão, mas não certeza absoluta.
        if proporcao >= HISTORICO_THRESHOLD:
            state["categoria"] = "Marketplace"
            state["sugestao_categoria"] = categoria_mais_frequente
            state["confianca"] = round(proporcao, 2)
            state["fonte"] = "historico_usuario"
            state["requer_confirmacao"] = True
            return state

        # Histórico variado: melhor não sugerir nada.
        state["categoria"] = "Marketplace"
        state["sugestao_categoria"] = None
        state["confianca"] = 1.0
        state["fonte"] = "marketplace_historico_diverso"
        state["requer_confirmacao"] = True
        return state


    async def aguardar_confirmacao(state: AgentState) -> dict:
        """
        Pausa o grafo e aguarda confirmação humana.
        O grafo pode ser retomado com app.ainvoke(Command(resume=resposta))
        """
        resposta = interrupt({
            "mensagem": "Confirme ou corrija a categoria sugerida",
            "nome_original": state.get('nome_original'),
            "nome_normalizado": state.get('nome_normalizado'),
            "valor": state.get('valor'),
            "categoria_sugerida": state.get('categoria'),
            "confianca": state.get('confianca'),
            "eh_marketplace": state.get('eh_marketplace', False)
        })

        categoria_final = resposta.get('categoria') or state.get('categoria')
        confirmado  = resposta.get('confirmado', True)

        return {
            "categoria": categoria_final,
            "confianca": 1.0 if confirmado else state.get('confianca', 0.5),
            'fonte': "humano",
            "requer_confirmacao": False,
        }

    def rota_apos_busca_vetorial(state: AgentState) -> str:
        """Se encontrou com alta confiança, salva. Senao, vai pro LLM"""
        if state.get('categoria') and state.get('confianca', 0) >= 0.85:
            return "salvar_resultado"
        return "classificar_com_llm"

    def rota_apos_llm(state: AgentState) -> str:
        """Se requer confirmação humana, aguarda. Senão, salva direto."""
        if state.get('requer_confirmacao'):
            return "aguardar_confirmacao"
        return "salvar_resultado"

    def rota_apos_normalizar(state: AgentState) -> str:
        """Se é marketplace, busca histórico do usuário. Senão, busca vetorial."""
        if state.get('eh_marketplace'):
            return "buscar_historico_marketplace"
        return "buscar_por_similaridade"

    def salvar_resultado(state: AgentState, writer: StreamWriter,) -> dict:
        writer(
            {
                **state,
                "mensagem":"mensagem de output"
            }
        )
        return {}


    def salvar_vectorstore(state: AgentState):
        pass
    
    return (buscar_estabelecimentos, 
            classificar_com_llm,
            buscar_historico_marketplace, 
            buscar_por_similaridade, 
            salvar_no_vectorstore,
            normalizar,
            classificar_marketplace_por_historico,
            aguardar_confirmacao,
            rota_apos_busca_vetorial,
            rota_apos_llm,
            rota_apos_normalizar,
            salvar_resultado,
            salvar_vectorstore
            )

    


