"""
Etapa 5 — Agente Híbrido Completo (LangGraph + RAG + Busca Web + CoT + HITL).

Modo A (--teste)   : roda o grafo sobre o teste-cego rotulado, sem gravar no BD.
                     Coleta acurácia/F1, latência média ponderada, distribuição de
                     método (vetorial/llm/humano) e taxa de Human-in-the-Loop.
Modo B (--gravar)  : roda o grafo sobre as transações Nubank reais do Postgres
                     (`transacoes` com status 'pendente') e PERSISTE a classificação
                     (categoria_id, confianca, metodo, status) via nó salvar_resultado.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from langchain_community.tools import BaseTool, DuckDuckGoSearchRun
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Command
from sqlalchemy import text

import common as C

sys.path.insert(0, str(C.REPO / "notebooks" / "modules"))
import nodes as nodes_mod  # noqa: E402
from async_service import AsyncService  # noqa: E402

LLM_MODEL = os.getenv("LLM_MODEL", "google/gemma-4-e4b")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:1234/v1")
HITL_LIMIAR = 0.80


USAR_WEB = os.getenv("AGENTE_WEB", "0") == "1"


def build_graph(active_learning: bool = True):
    tools: list[BaseTool] = []
    if USAR_WEB:
        tools.append(DuckDuckGoSearchRun(
            name="duckduckgo_search",
            description="Pesquisa de estabelecimentos na web para obter o ramo de atuação.",
        ))
    services = AsyncService(
        db_url=C.exigir_env("DATABASE_URL"),
        llm_model=LLM_MODEL,
        api_key=os.getenv("LLM_API_KEY", "lm-studio"),
        llm_provider="openai",
        base_url=LLM_BASE_URL,
        tools=tools,
    )
    (
        _buscar_estabelecimentos, classificar_com_llm, buscar_historico_marketplace,
        buscar_por_similaridade, normalizar, _classificar_marketplace_por_historico,
        aguardar_confirmacao, rota_apos_busca_vetorial, _rota_apos_llm,
        rota_apos_normalizar, salvar_resultado, salvar_vectorstore,
        estruturar_saida_llm, roteador_unificado_llm,
    ) = nodes_mod.make_nodes(services)

    HITL_LIMIAR_LLM = HITL_LIMIAR

    def roteador_pos_llm(state):
        msgs = state.get("messages", [])
        if msgs and getattr(msgs[-1], "tool_calls", None):
            return "tools"
        return "estruturar_saida_llm"

    def rota_apos_estruturar(state):
        """HITL só quando a confiança DO LLM é baixa ou ele pede confirmação."""
        conf = state.get("confianca")
        try:
            conf = float(conf) if conf is not None else 0.0
        except (TypeError, ValueError):
            conf = 0.0
        if state.get("requer_confirmacao") or conf <= HITL_LIMIAR_LLM:
            return "aguardar_confirmacao"
        return "salvar_vectorstore"

    g = StateGraph(nodes_mod.AgentState)
    g.add_node("normalizar", normalizar)
    g.add_node("buscar_por_similaridade", buscar_por_similaridade)
    g.add_node("buscar_historico_marketplace", buscar_historico_marketplace)
    g.add_node("classificar_com_llm", classificar_com_llm)
    g.add_node("aguardar_confirmacao", aguardar_confirmacao)
    g.add_node("estruturar_saida_llm", estruturar_saida_llm)
    async def _noop_vs(state):
        return {}
    g.add_node("salvar_vectorstore", salvar_vectorstore if active_learning else _noop_vs)
    g.add_node("salvar_resultado", salvar_resultado)
    g.add_node("tools", ToolNode(tools))

    g.set_entry_point("normalizar")
    g.add_edge("buscar_historico_marketplace", "buscar_por_similaridade")
    g.add_edge("aguardar_confirmacao", "salvar_vectorstore")
    g.add_edge("tools", "classificar_com_llm")
    g.add_edge("salvar_vectorstore", "salvar_resultado")
    g.add_edge("salvar_resultado", END)
    g.add_conditional_edges("normalizar", rota_apos_normalizar, {
        "buscar_historico_marketplace": "buscar_historico_marketplace",
        "buscar_por_similaridade": "buscar_por_similaridade"})
    g.add_conditional_edges("buscar_por_similaridade", rota_apos_busca_vetorial, {
        "salvar_resultado": "salvar_resultado", "classificar_com_llm": "classificar_com_llm"})
    g.add_conditional_edges("classificar_com_llm", roteador_pos_llm, {
        "tools": "tools", "estruturar_saida_llm": "estruturar_saida_llm"})
    g.add_conditional_edges("estruturar_saida_llm", rota_apos_estruturar, {
        "aguardar_confirmacao": "aguardar_confirmacao",
        "salvar_vectorstore": "salvar_vectorstore"})
    return g.compile(checkpointer=MemorySaver())


async def _classificar_um(app, payload, thread, timeout=120, confirmar_hitl=True):
    t0 = time.perf_counter()
    hitl = False
    try:
        res = await asyncio.wait_for(app.ainvoke(payload, config=thread), timeout)
        st = app.get_state(thread)
        if st.next:  # pausado em aguardar_confirmacao
            hitl = True
            sug = st.values.get("categoria")
            res = await asyncio.wait_for(
                app.ainvoke(Command(resume={"confirmado": confirmar_hitl, "categoria": sug}),
                            config=thread), timeout)
    except Exception as e:  # noqa
        return {"categoria": None, "erro": str(e)[:200],
                "lat_ms": (time.perf_counter() - t0) * 1000, "hitl": hitl}
    dt = (time.perf_counter() - t0) * 1000
    return {"categoria": res.get("categoria"), "confianca": res.get("confianca"),
            "fonte": res.get("fonte"), "metodo": res.get("metodo_classificacao"),
            "requer_confirmacao": res.get("requer_confirmacao"),
            "lat_ms": dt, "hitl": hitl}


async def rodar_teste(n: int | None = None):
    _, _, test = C.carregar_splits()
    if n:
        test = test.groupby("categoria", group_keys=False).apply(
            lambda g: g.head(max(1, n // test["categoria"].nunique()))
        ).reset_index(drop=True)
    app = build_graph(active_learning=False)  # sem auto-escrita no vectorstore (evita leakage no teste)
    print(f"agente :: teste-cego com {len(test)} transações  (LLM={LLM_MODEL})")
    regs = []
    for i, row in test.reset_index(drop=True).iterrows():
        thread = {"configurable": {"thread_id": f"teste:{i}"}}
        payload = {
            "usuario_id": "1", "nome_original": str(row["descricao"]),
            "valor": float(row["valor"]),
            "source": "bronze/source=c6/year=2024/month=01/day=15/x/original.csv",
            "messages": [HumanMessage(content=f"Classifique esta transação: {row['descricao']}")],
        }
        r = await _classificar_um(app, payload, thread)
        r["y_true"] = row["categoria"]
        r["descricao"] = row["descricao"]
        regs.append(r)
        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{len(test)}")

    df = C.pd.DataFrame(regs)
    df["y_pred"] = df["categoria"].map(_ancorar).fillna("Despesas Diversas / Outros")
    df.to_csv(C.RESULTS / "agente_teste_bruto.csv", index=False)

    lat = float(df["lat_ms"].mean())
    hitl_rate = float(df["hitl"].mean())
    metodo_dist = df["fonte"].value_counts(normalize=True).to_dict()
    import json as _json
    (C.RESULTS / "agente_metricas.json").write_text(_json.dumps({
        "n_teste": int(len(df)),
        "acuracia": float((df["y_pred"] == df["y_true"]).mean()),
        "latencia_ms_media": lat,
        "latencia_ms_mediana": float(df["lat_ms"].median()),
        "taxa_hitl": hitl_rate,
        "frac_vetorial": float(metodo_dist.get("vetorial", 0.0)),
        "frac_llm": float(metodo_dist.get("llm", 0.0)) + float(metodo_dist.get("humano", 0.0)),
        "erros_execucao": int(df["categoria"].isna().sum()),
        "llm_model": LLM_MODEL,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    C.registrar_resultado(
        "agente_hibrido_langgraph",
        {"llm": LLM_MODEL, "grafo": "normalizar->rag->llm+tools->hitl",
         "limiar_rag": 0.85, "limiar_hitl": HITL_LIMIAR},
        df["y_true"].tolist(), df["y_pred"].tolist(), lat,
        tags={"familia": "agente"},
        extra_metrics={
            "taxa_hitl": hitl_rate,
            "frac_vetorial": float(metodo_dist.get("vetorial", 0.0)),
            "frac_llm": float(metodo_dist.get("llm", 0.0)),
            "frac_humano": float(metodo_dist.get("humano", 0.0)),
            "erros_execucao": int(df["categoria"].isna().sum()),
        },
    )
    print(f"HITL={hitl_rate:.1%}  métodos={metodo_dist}")


def _ancorar(txt):
    if not txt:
        return None
    from rapidfuzz import fuzz, process
    m = process.extractOne(str(txt), C.CATEGORIAS, scorer=fuzz.WRatio)
    return m[0] if m and m[1] >= 55 else "Despesas Diversas / Outros"


async def rodar_gravar(limite: int | None):
    app = build_graph()
    eng = C.engine_sync()
    with eng.connect() as cx:
        # amostra pseudoaleatória reprodutível (md5 do id) quando limite é definido
        ordem = "md5(t.id::text)" if limite else "t.id"
        q = ("SELECT t.id, t.nome_original, t.valor, t.data_transacao, f.arquivo_origem, "
             "f.usuario_id FROM transacoes t JOIN faturas f ON f.id=t.fatura_id "
             f"WHERE t.status_classificacao='pendente' ORDER BY {ordem}")
        if limite:
            q += f" LIMIT {limite}"
        linhas = cx.execute(text(q)).fetchall()
    print(f"gravando classificação de {len(linhas)} transações...")

    n_ok = n_hitl = 0
    for k, (tid, nome, valor, data_tx, origem, uid) in enumerate(linhas):
        thread = {"configurable": {"thread_id": f"bd:{tid}"}}
        payload = {
            "usuario_id": str(uid), "transacao_id": str(tid),
            "nome_original": str(nome), "valor": float(valor),
            "data_transacao": str(data_tx), "source": str(origem),
            "messages": [HumanMessage(content=f"Classifique esta transação: {nome}")],
        }
        r = await _classificar_um(app, payload, thread, confirmar_hitl=False)
        n_ok += int(r["categoria"] is not None)
        n_hitl += int(r["hitl"])
        if (k + 1) % 50 == 0:
            print(f"  {k+1}/{len(linhas)}  ok={n_ok} hitl={n_hitl}")
    print(f"concluído: {n_ok}/{len(linhas)} classificadas, {n_hitl} via HITL")

    mlflow = C.init_mlflow()
    with mlflow.start_run(run_name="agente::gravacao_bd_nubank"):
        mlflow.set_tag("etapa", "classificacao_cap4")
        mlflow.log_param("total_transacoes", len(linhas))
        mlflow.log_metric("classificadas", n_ok)
        mlflow.log_metric("taxa_hitl_producao", n_hitl / max(1, len(linhas)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--teste", action="store_true")
    ap.add_argument("--gravar", action="store_true")
    ap.add_argument("--limite", type=int, default=None)
    ap.add_argument("--n", type=int, default=None, help="limita nº de transações do teste (smoke)")
    a = ap.parse_args()
    if a.teste:
        asyncio.run(rodar_teste(a.n))
    if a.gravar:
        asyncio.run(rodar_gravar(a.limite))
