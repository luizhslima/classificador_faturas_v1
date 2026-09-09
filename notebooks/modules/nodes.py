from datetime import datetime
from sqlalchemy import select
from model import (
    Categoria,
    Estabelecimento,
    Subcategoria,
    SugestaoCategoriaMarketplace,
    TipoEstabelecimento,
    Transacao,
)
try:
    from modules.async_service import AsyncService
except ModuleNotFoundError:
    try:
        from async_service import AsyncService
    except ModuleNotFoundError:
        from notebooks.modules.async_service import AsyncService

try:
    from modules.state import AgentState
except ModuleNotFoundError:
    try:
        from state import AgentState
    except ModuleNotFoundError:
        from notebooks.modules.state import AgentState
from utils import normalizar_nome, extrair_metadados_datalake, gerar_regra_ocr
from collections import Counter
from langgraph.types import interrupt
from langsmith import traceable
from structures import ClassificacaoLLM
from langchain_core.messages import HumanMessage, SystemMessage
from decimal import Decimal
from langgraph.types import StreamWriter
from langchain_community.tools import DuckDuckGoSearchRun, BaseTool


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




def make_nodes(services: AsyncService):

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
        
    async def classificar_com_llm(state: AgentState):
        dtlk = extrair_metadados_datalake(state.get('source', ''))
        instrucao_ocr = gerar_regra_ocr(dtlk["is_digital_nativo"])
        async with services.session_factory() as session:
            result = await session.execute(
                select(Categoria).where(Categoria.ativo.is_(True)).order_by(Categoria.id)
            )
            tipos = result.scalars().all()
            if not tipos:
                result = await session.execute(select(TipoEstabelecimento))
                tipos = result.scalars().all()
            try:
                classificador = services.llm.bind_tools(services.tools)
            except Exception:
                classificador = services.llm
            sistem_msg = SystemMessage(
                content=f"""
                        Você é um assistente financeiro especialista em classificar transações de faturas de cartão de crédito no Brasil.
                        CONTEXTO DA EXTRAÇÃO:
                        - Banco Origem: {dtlk.get('source')}
                        - Formato do Dado: {dtlk['extensao']}
                        Você tem acesso a ferramentas. Sempre que usar uma ferramenta, certifique-se de preencher os parâmetros com um JSON estrito, utilizando os tipos corretos (ex: booleanos não devem ter aspas).
                        REGRAS DE ANÁLISE:
                        1. PROCESSADORES DE PAGAMENTO: Prefixos como "PG*", "PAG*", "MP*", "ZOOP*", "SUMUP*", "IFD*", "EBN*", "HNA*" indicam apenas a maquininha/gateway. Descodifique siglas comuns (IFD/IFOOD=comida, UBR/UBER=transporte, AMZN=marketplace, DROGA=farmácia).
                        2. SUA TAREFA É A CATEGORIA, NÃO A MARCA: mesmo sem reconhecer o estabelecimento específico, use pistas genéricas do texto para inferir a categoria. Palavras como "RESTAURANTE", "LANCHONETE", "PIZZA", "ACAI", "PADARIA", "MERCADO", "HORTIFRUTI" => Alimentação; "DROGARIA", "DROGA", "FARMACIA", "OTICA", "CLINICA" => Saúde; "POSTO", "AUTO POSTO", "UBER", "99" => Transporte; "INGRESSE", "INGRESSO", "CINEMA", "STEAM", "PLAYSTATION", "JOGOS", "GAMES" => Lazer e Entretenimento; "MERCADOLIVRE", "AMAZON", "SHOPEE", "MAGALU" => Marketplace / E-commerce. Só use "Despesas Diversas / Outros" quando NENHUMA pista de categoria estiver presente.
                        3. COMBATE A ALUCINAÇÕES: não invente a identidade da marca; mas inferir a categoria a partir de pistas genéricas NÃO é alucinação.
                        4. REGRA DE ORIGEM DO DADO: {instrucao_ocr}
                        6. ESTABELECIMENTOS TOTALMENTE OPACOS: apenas quando o nome for um gateway genérico sem pista (ex.: "DIVIPAYPAYMENTS", "PAYPAL *XXXX") ou um nome próprio informal sem contexto, defina 'requer_confirmacao=true' e confiança <= 0.70.
                        7. CADEIA DE PENSAMENTO: Pense passo a passo (raciocínio curto) ANTES de decidir a categoria.
                        8. Se houver a ferramenta 'duckduckgo_search', use-a no máximo UMA vez, sem aspas na busca, para nomes obscuros.
                        9. SAÍDA FINAL: termine sua resposta com um bloco JSON em uma única linha, no formato exato:
                        {{"categoria": "<um rótulo EXATO da lista abaixo>", "subcategoria": null, "confianca": <0..1>, "requer_confirmacao": <true|false>, "justificativa": "<curta>", "possiveis_categorias": ["...","...","..."], "raciocinio": "<resumo>"}}

                        CATEGORIAS PERMITIDAS (Você DEVE escolher apenas uma desta lista ):
                        {';'.join([f'Nome:{tipo.nome} - descrição: {tipo.descricao}' for tipo in tipos])}
                        """)
            msgs = [sistem_msg] + state.get('messages', [])
            try:
                response = await classificador.ainvoke(msgs)
            except Exception:
                # LM Studio pode rejeitar o grammar de tool-calling; tenta sem ferramentas
                response = await services.llm.ainvoke(msgs)
            return {"messages": [response]}

    async def estruturar_saida_llm(state: AgentState) -> dict:
        mensagens = state.get("messages", [])
        if not mensagens:
            return {
                "fonte": "llm",
                "requer_confirmacao": True,
                "erro": "Nenhuma mensagem encontrada para estruturar.",
            }

        ultima_mensagem = mensagens[-1]

        def _texto_msg(msg) -> str:
            partes = []
            c = getattr(msg, "content", None)
            if isinstance(c, str) and c.strip():
                partes.append(c)
            elif isinstance(c, list):
                partes.extend(str(x.get("text", x)) if isinstance(x, dict) else str(x) for x in c)
            ak = getattr(msg, "additional_kwargs", {}) or {}
            for k in ("reasoning_content", "reasoning"):
                if ak.get(k):
                    partes.append(str(ak[k]))
            return "\n".join(partes) if partes else str(msg)

        conteudo_texto = _texto_msg(ultima_mensagem)

        import json as _json
        import re as _re
        from difflib import get_close_matches

        async with services.session_factory() as _s:
            _cats = [c.nome for c in (
                await _s.execute(select(Categoria).order_by(Categoria.id))
            ).scalars().all()]
        _cats = _cats or [
            "Alimentação", "Transporte", "Saúde", "Moradia", "Lazer e Entretenimento",
            "Tecnologia", "Marketplace / E-commerce", "Vestuário",
            "Beleza e Cuidados Pessoais", "Educação", "Pets", "Serviços Financeiros",
            "Doações e Presentes", "Despesas Diversas / Outros",
        ]

        def _ancora_cat(valor: str) -> str:
            valor = (valor or "").strip()
            for c in _cats:
                if c.lower() == valor.lower():
                    return c
            mm = get_close_matches(valor, _cats, n=1, cutoff=0.6)
            if mm:
                return mm[0]
            vl = valor.lower()
            for c in _cats:
                if vl and (vl in c.lower() or c.lower().split()[0] in vl):
                    return c
            return "Despesas Diversas / Outros"

        prompt_extracao = (
            "Com base na análise abaixo, responda APENAS com um objeto JSON válido "
            "(sem markdown, sem comentários) com as chaves: categoria, subcategoria "
            "(ou null), confianca (número 0..1), justificativa, requer_confirmacao "
            "(booleano), possiveis_categorias (lista), raciocinio.\n"
            "O campo 'categoria' DEVE ser exatamente um destes rótulos: "
            + "; ".join(_cats)
            + "\n\nAnálise:\n" + str(conteudo_texto)
        )

        async def _parse_manual():
            raw = await services.llm.ainvoke(prompt_extracao)
            txt = _texto_msg(raw)
            m = _re.search(r"\{[^{}]*\"categoria\".*\}", txt, _re.DOTALL) or \
                _re.search(r"\{.*\}", txt, _re.DOTALL)
            if not m:
                raise ValueError("sem JSON na resposta")
            data = _json.loads(m.group(0))
            return ClassificacaoLLM(
                categoria=_ancora_cat(str(data.get("categoria") or "")),
                subcategoria=(data.get("subcategoria") or None),
                confianca=float(data.get("confianca", 0.5) or 0.5),
                justificativa=str(data.get("justificativa") or ""),
                requer_confirmacao=bool(data.get("requer_confirmacao", False)),
                possiveis_categorias=list(data.get("possiveis_categorias") or []),
                raciocinio=str(data.get("raciocinio") or conteudo_texto),
            )

        def _json_do_texto(txt: str):
            m = _re.search(r"\{[^{}]*\"categoria\"[^{}]*\}", txt, _re.DOTALL) or \
                _re.search(r"\{.*\}", txt, _re.DOTALL)
            if not m:
                return None
            try:
                d = _json.loads(m.group(0))
            except Exception:
                return None
            if "categoria" not in d:
                return None
            return ClassificacaoLLM(
                categoria=_ancora_cat(str(d.get("categoria") or "")),
                subcategoria=(d.get("subcategoria") or None),
                confianca=float(d.get("confianca", 0.6) or 0.6),
                justificativa=str(d.get("justificativa") or ""),
                requer_confirmacao=bool(d.get("requer_confirmacao", False)),
                possiveis_categorias=list(d.get("possiveis_categorias") or []),
                raciocinio=str(d.get("raciocinio") or txt)[:2000],
            )

        try:
            # 1) tenta extrair o JSON que o próprio nó de classificação já produziu
            resposta_estruturada = _json_do_texto(conteudo_texto)
            # 2) só chama o LLM de novo se necessário
            if resposta_estruturada is None:
                try:
                    model_with_structured = services.llm.with_structured_output(ClassificacaoLLM)
                    resposta_estruturada = await model_with_structured.ainvoke(prompt_extracao)
                except Exception:
                    resposta_estruturada = await _parse_manual()

            if isinstance(resposta_estruturada, dict):
                categoria = resposta_estruturada.get("categoria")
                subcategoria = resposta_estruturada.get("subcategoria")
                confianca = float(str(resposta_estruturada.get("confianca", 0.0)))
                requer_confirmacao = bool(resposta_estruturada.get("requer_confirmacao", False))
                justificativa = resposta_estruturada.get("justificativa", "")
                possiveis_categorias = resposta_estruturada.get("possiveis_categorias", [])
                raciocinio = resposta_estruturada.get("raciocinio", "")
            else:
                categoria = getattr(resposta_estruturada, "categoria", None)
                subcategoria = getattr(resposta_estruturada, "subcategoria", None)
                confianca = float(str(getattr(resposta_estruturada, "confianca", 0.0)))
                requer_confirmacao = bool(getattr(resposta_estruturada, "requer_confirmacao", False))
                justificativa = getattr(resposta_estruturada, "justificativa", "")
                possiveis_categorias = getattr(resposta_estruturada, "possiveis_categorias", [])
                raciocinio = getattr(resposta_estruturada, "raciocinio", "")

            categoria = _ancora_cat(categoria if isinstance(categoria, str) else "")

            return {
                "categoria": categoria,
                "subcategoria": subcategoria,
                "confianca": confianca,
                "fonte": "llm",
                "requer_confirmacao": requer_confirmacao,
                "justificativa_classificacao": justificativa,
                "possiveis_categorias": possiveis_categorias,
                "raciocinio": raciocinio or conteudo_texto,
            }
        except Exception as e:
            return {
                "fonte": "llm",
                "requer_confirmacao": True,
                "erro": f"Erro ao estruturar saída da LLM: {str(e)}",
                "raciocinio": conteudo_texto,
            }

    @traceable(
            name="Buscar historico de marketplace",
            run_type="retriever"
    )
    async def buscar_historico_marketplace(state: AgentState) -> dict:
        try:
            uid = int(state.get('usuario_id'))
        except (TypeError, ValueError):
            return {"historico_marketplace": {}}
        async with services.session_factory() as session:
            result = await session.execute(
                select(SugestaoCategoriaMarketplace)
                .where(
                    SugestaoCategoriaMarketplace.usuario_id == uid,
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
        query = state.get('nome_normalizado', 'invalido')
        try:
            pares = await services.vectorstore.asimilarity_search_with_relevance_scores(
                query, k=3
            )
        except Exception:
            pares = []

        if not pares:
            return {}

        melhor, score = pares[0]
        try:
            score = max(0.0, min(1.0, float(score)))
        except (TypeError, ValueError):
            score = 0.0

        categoria = melhor.metadata.get('categoria') or melhor.metadata.get('categoria_nome')
        if not categoria:
            return {}

        return {
            "categoria": categoria,
            "confianca": score,
            "fonte": "vetorial",
            "metodo_classificacao": "vetorial",
            "requer_confirmacao": score < services.SIMILARITY_THRESHOLD,
        }
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

        if confirmado:
            return {
                "categoria": categoria_final,
                "confianca": 1.0,
                'fonte': "humano",
                "metodo_classificacao": "humano",
                "requer_confirmacao": False,
                "status_classificacao": "confirmada_usuario",
            }
        # sem confirmação humana efetiva: mantém sugestão do LLM p/ revisão posterior
        return {
            "categoria": categoria_final,
            "confianca": state.get('confianca', 0.5),
            'fonte': "llm",
            "metodo_classificacao": "llm",
            "requer_confirmacao": True,
            "status_classificacao": "sugerida",
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
        return "estruturar_saida_llm"

    def rota_apos_normalizar(state: AgentState) -> str:
        """Se é marketplace, busca histórico do usuário. Senão, busca vetorial."""
        if state.get('eh_marketplace'):
            return "buscar_historico_marketplace"
        return "buscar_por_similaridade"

    async def salvar_resultado(state: AgentState) -> dict:
        async with services.session_factory() as session:
            # 1. Resolução de categoria_id
            categoria_id = None
            categoria_val = state.get("categoria")
            if isinstance(categoria_val, int):
                categoria_id = categoria_val
            elif isinstance(categoria_val, str) and categoria_val.strip():
                cat_result = await session.execute(
                    select(Categoria.id).where(Categoria.nome.ilike(categoria_val.strip()))
                )
                categoria_id = cat_result.scalar_one_or_none()

            # 2. Resolução de subcategoria_id
            subcategoria_id = None
            subcategoria_val = state.get("subcategoria")
            if isinstance(subcategoria_val, int):
                subcategoria_id = subcategoria_val
            elif isinstance(subcategoria_val, str) and subcategoria_val.strip():
                subcat_stmt = select(Subcategoria.id).where(Subcategoria.nome.ilike(subcategoria_val.strip()))
                if categoria_id:
                    subcat_stmt = subcat_stmt.where(Subcategoria.categoria_id == categoria_id)
                subcat_result = await session.execute(subcat_stmt)
                subcategoria_id = subcat_result.scalar_one_or_none()

            # 3. Resolução de sugestão de categoria (marketplaces)
            categoria_sugerida_id = None
            cat_sug_val = state.get("categoria_sugerida")
            if isinstance(cat_sug_val, int):
                categoria_sugerida_id = cat_sug_val
            elif isinstance(cat_sug_val, str) and cat_sug_val.strip():
                cat_sug_res = await session.execute(
                    select(Categoria.id).where(Categoria.nome.ilike(cat_sug_val.strip()))
                )
                categoria_sugerida_id = cat_sug_res.scalar_one_or_none()

            subcategoria_sugerida_id = None
            subcat_sug_val = state.get("subcategoria_sugerida")
            if isinstance(subcat_sug_val, int):
                subcategoria_sugerida_id = subcat_sug_val
            elif isinstance(subcat_sug_val, str) and subcat_sug_val.strip():
                subcat_sug_stmt = select(Subcategoria.id).where(Subcategoria.nome.ilike(subcat_sug_val.strip()))
                if categoria_sugerida_id:
                    subcat_sug_stmt = subcat_sug_stmt.where(Subcategoria.categoria_id == categoria_sugerida_id)
                subcat_sug_res = await session.execute(subcat_sug_stmt)
                subcategoria_sugerida_id = subcat_sug_res.scalar_one_or_none()

            # 4. Resolução de estabelecimento_id
            estabelecimento_id = None
            est_id_val = state.get("estabelecimento_id")
            if est_id_val is not None:
                try:
                    estabelecimento_id = int(est_id_val)
                except (ValueError, TypeError):
                    estabelecimento_id = None
            if estabelecimento_id is None:
                nome_est = state.get("nome_normalizado") or state.get("estabelecimento")
                if nome_est:
                    est_res = await session.execute(
                        select(Estabelecimento.id).where(Estabelecimento.nome_normalizado == nome_est)
                    )
                    estabelecimento_id = est_res.scalar_one_or_none()

            # 5. Formatação e normalização de confianças
            confianca_val = None
            if state.get("confianca") is not None:
                try:
                    c = max(0.0, min(1.0, float(state.get("confianca"))))
                    confianca_val = Decimal(str(round(c, 3)))
                except (ValueError, TypeError):
                    pass

            confianca_sugestao_val = None
            if state.get("confianca_sugestao") is not None:
                try:
                    cs = max(0.0, min(1.0, float(state.get("confianca_sugestao"))))
                    confianca_sugestao_val = Decimal(str(round(cs, 3)))
                except (ValueError, TypeError):
                    pass

            # 6. Método de classificação e validação de status
            fonte = state.get("fonte")
            metodo_classificacao = state.get("metodo_classificacao") or fonte
            requer_confirmacao = bool(state.get("requer_confirmacao", False))

            status_classificacao = state.get("status_classificacao")
            if not status_classificacao:
                if fonte == "humano":
                    status_classificacao = "confirmada_usuario"
                elif requer_confirmacao:
                    if state.get("eh_marketplace") or state.get("categoria_sugerida"):
                        status_classificacao = "sugerida"
                    else:
                        status_classificacao = "pendente"
                elif state.get("categoria"):
                    status_classificacao = "classificada"
                else:
                    status_classificacao = "pendente"

            origem_detalhamento = state.get("origem_detalhamento")
            origens_validas = {
                "fatura", "historico_usuario", "nota_fiscal",
                "email", "api_marketplace", "usuario", "estimativa"
            }
            if origem_detalhamento not in origens_validas:
                origem_detalhamento = None

            # 7. Buscar e atualizar Transacao existente ou criar nova
            transacao_id = state.get("transacao_id") or state.get("id")
            transacao = None
            if transacao_id is not None:
                try:
                    tid = int(transacao_id)
                    result = await session.execute(
                        select(Transacao).where(Transacao.id == tid)
                    )
                    transacao = result.scalar_one_or_none()
                except (ValueError, TypeError):
                    transacao = None

            if transacao is not None:
                if categoria_id is not None:
                    transacao.categoria_id = categoria_id
                if subcategoria_id is not None:
                    transacao.subcategoria_id = subcategoria_id
                if estabelecimento_id is not None:
                    transacao.estabelecimento_id = estabelecimento_id
                if confianca_val is not None:
                    transacao.confianca = confianca_val
                if metodo_classificacao:
                    transacao.metodo_classificacao = str(metodo_classificacao)
                if categoria_sugerida_id is not None:
                    transacao.categoria_sugerida_id = categoria_sugerida_id
                if subcategoria_sugerida_id is not None:
                    transacao.subcategoria_sugerida_id = subcategoria_sugerida_id
                if confianca_sugestao_val is not None:
                    transacao.confianca_sugestao = confianca_sugestao_val
                if origem_detalhamento:
                    transacao.origem_detalhamento = origem_detalhamento
                if state.get("nome_normalizado"):
                    transacao.nome_normalizado = state.get("nome_normalizado")
                transacao.requer_confirmacao = requer_confirmacao
                transacao.status_classificacao = status_classificacao
                if fonte == "humano":
                    transacao.revisado_usuario = True
            else:
                fatura_id = state.get("fatura_id")
                nome_original = state.get("nome_original")
                valor = state.get("valor")
                data_transacao = state.get("data_transacao") or datetime.now().date()
                if isinstance(data_transacao, datetime):
                    data_transacao = data_transacao.date()
                elif isinstance(data_transacao, str):
                    try:
                        data_transacao = datetime.fromisoformat(data_transacao).date()
                    except Exception:
                        data_transacao = datetime.now().date()

                if fatura_id and nome_original and valor is not None:
                    transacao = Transacao(
                        fatura_id=int(fatura_id),
                        nome_original=str(nome_original),
                        nome_normalizado=state.get("nome_normalizado"),
                        valor=Decimal(str(valor)),
                        data_transacao=data_transacao,
                        categoria_id=categoria_id,
                        subcategoria_id=subcategoria_id,
                        estabelecimento_id=estabelecimento_id,
                        confianca=confianca_val,
                        metodo_classificacao=str(metodo_classificacao) if metodo_classificacao else None,
                        categoria_sugerida_id=categoria_sugerida_id,
                        subcategoria_sugerida_id=subcategoria_sugerida_id,
                        confianca_sugestao=confianca_sugestao_val,
                        origem_detalhamento=origem_detalhamento,
                        requer_confirmacao=requer_confirmacao,
                        status_classificacao=status_classificacao,
                        revisado_usuario=True if fonte == "humano" else False,
                    )
                    session.add(transacao)

            await session.commit()

        return {"status_classificacao": status_classificacao}


    async def salvar_vectorstore(state: AgentState):
        nome = state.get("nome_normalizado")
        if nome is None:
            raise ValueError("nome_normalizado é obrigatório para salvar no vectorstore")

        confianca = state.get("confianca")
        try:
            confianca_val = float(confianca) if confianca is not None else 0.0
        except (ValueError, TypeError):
            confianca_val = 0.0

        if confianca_val <= 0.85:
            return {}

        metadata = {
            "categoria": state.get("categoria"),
            "confianca": str(confianca) if confianca is not None else None,
            "fonte": state.get("fonte"),
            "eh_marketplace": state.get("eh_marketplace", False),
            "data_cadastro": datetime.now().isoformat(),
        }

        await services.vectorstore.aadd_texts(
            texts=[nome],
            metadatas=[metadata],
        )
        return {}

    def roteador_unificado_llm(state: AgentState):
        messages = state.get("messages", [])
        if messages:
            last_message = messages[-1]
            # Verifica se o LLM decidiu usar uma ferramenta (mesmo comportamento do tools_condition)
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"
                
        # Se não chamou ferramenta, roda a sua função customizada original
        return rota_apos_llm(state)
    
    return (
        buscar_estabelecimentos,
        classificar_com_llm,
        buscar_historico_marketplace,
        buscar_por_similaridade,
        normalizar,
        classificar_marketplace_por_historico,
        aguardar_confirmacao,
        rota_apos_busca_vetorial,
        rota_apos_llm,
        rota_apos_normalizar,
        salvar_resultado,
        salvar_vectorstore,
        estruturar_saida_llm,
        roteador_unificado_llm,
    )

    


