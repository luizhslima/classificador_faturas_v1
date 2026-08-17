import asyncio
from decimal import Decimal
from langgraph.types import Command
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langchain_core.runnables import RunnableConfig
from decimal import Decimal
from state import AgentState

async def classificar_batch(
    app: CompiledStateGraph[AgentState, None, AgentState, AgentState],
    transacoes: list[dict],
    max_concorrentes: int = 5,
) -> list[dict]:
    semaforo = asyncio.Semaphore(max_concorrentes)

    async def classificar_uma(transacao: dict, indice: int) -> dict:
        async with semaforo:
            thread: RunnableConfig = {
                "configurable": {
                    "thread_id": f"batch:{transacao['fatura_id']}:{transacao['id']}",
                }
            }

            resultado = await app.ainvoke(
                {
                    "usuario_id": str(transacao["usuario_id"]),
                    "nome_original": transacao["nome_original"],
                    "valor": Decimal(str(transacao["valor"])),
                },
                config=thread,
            )

            estado = app.get_state(thread)

            # Pausou em aguardar_confirmacao
            if estado.next:
                return {
                    "indice": indice,
                    "transacao_id": transacao["id"],
                    "nome_original": transacao["nome_original"],
                    "status": "pendente_confirmacao",
                    "categoria_sugerida": estado.values.get("categoria"),
                    "confianca": str(estado.values.get("confianca")),
                    "justificativa": estado.values.get("justificativa_classificacao"),
                    "possiveis_categorias": estado.values.get("possiveis_categorias", []),
                    "thread_id": thread["configurable"]["thread_id"],
                }

            return {
                "indice": indice,
                "transacao_id": transacao["id"],
                "nome_original": transacao["nome_original"],
                "status": "classificada",
                "categoria": resultado.get("categoria"),
                "subcategoria": resultado.get("subcategoria"),
                "confianca": str(resultado.get("confianca")),
                "fonte": resultado.get("fonte"),
            }

    tarefas = [
        classificar_uma(transacao, i)
        for i, transacao in enumerate(transacoes)
    ]

    return await asyncio.gather(*tarefas)


async def classificar_batch_nativo(
    app: CompiledStateGraph[AgentState, None, AgentState, AgentState],
    transacoes: list[dict],
) -> list[dict]:
    entradas: list[AgentState] = [
        {
            "usuario_id": str(t["usuario_id"]),
            "nome_original": t["nome_original"],
            "valor": Decimal(str(t["valor"])),
        }
        for t in transacoes
    ]

    configs: list[RunnableConfig] = [
        {
            "configurable": {
                "thread_id": f"batch:{t['fatura_id']}:{t['id']}",
            }
        }
        for t in transacoes
    ]

    resultados = await app.abatch(
        entradas,
        config=configs,
    )

    return resultados

async def processar_fatura(
    app: CompiledStateGraph[AgentState, None, AgentState, AgentState],
    fatura_id: int,
    transacoes: list[dict],
) -> dict:
    resultados = await classificar_batch(app, transacoes)

    classificadas = [
        r for r in resultados
        if r["status"] == "classificada"
    ]

    pendentes = [
        r for r in resultados
        if r["status"] == "pendente_confirmacao"
    ]

    print(f"✅ Classificadas automaticamente : {len(classificadas)}")
    print(f"⏸️  Aguardando confirmação        : {len(pendentes)}")

    return {
        "fatura_id": fatura_id,
        "classificadas": classificadas,
        "pendentes_confirmacao": pendentes,
    }


async def confirmar_batch(
    app: CompiledStateGraph[AgentState, None, AgentState, AgentState],
    pendentes: list[dict],
    confirmacoes: list[dict],
) -> list[dict]:
    """
    confirmacoes: lista com {"thread_id": ..., "categoria": ..., "confirmado": ...}
    """
    semaforo = asyncio.Semaphore(5)

    async def retomar_uma(confirmacao: dict) -> dict:
        async with semaforo:
            thread: RunnableConfig = {
                "configurable": {
                    "thread_id": confirmacao["thread_id"],
                }
            }

            resultado = await app.ainvoke(
                Command(
                    resume={
                        "confirmado": confirmacao.get("confirmado", True),
                        "categoria": confirmacao["categoria"],
                        "subcategoria": confirmacao.get("subcategoria"),
                    }
                ),
                config=thread,
            )

            return {
                "thread_id": confirmacao["thread_id"],
                "status": "confirmada",
                "categoria": resultado.get("categoria"),
                "fonte": resultado.get("fonte"),
            }

    tarefas = [retomar_uma(c) for c in confirmacoes]

    return await asyncio.gather(*tarefas)