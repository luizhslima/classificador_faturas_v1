"""
Etapa 4 — Busca Vetorial RAG com PGVector (embeddings densos MiniLM).

- Vetoriza cada estabelecimento único do split de treino com
  `paraphrase-multilingual-MiniLM-L12-v2` (384-d).
- Persiste a base de conhecimento em duas frentes:
    * tabela relacional `estabelecimentos` (nome, categoria, embedding, fonte)
    * coleção PGVector `baseconhecimento` (usada também pelo agente na etapa 5)
- Classifica o teste-cego por k-NN de cosseno (k=3, voto ponderado por similaridade).
  Latência = tempo médio de consulta vetorial por transação.
"""
from __future__ import annotations

import argparse
import time
from collections import defaultdict

import numpy as np

import common as C

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION = "baseconhecimento"
K = 3
LIMIAR = 0.85  # limiar de alta confiança citado na metodologia


def _embedder():
    from sentence_transformers import SentenceTransformer

    # CPU: evita disputa de VRAM com o fine-tuning do ByT5 e é rápido o suficiente
    return SentenceTransformer(MODEL_NAME, device="cpu")


def base_conhecimento(tr, emb):
    """Agrega estabelecimentos únicos do treino e vetoriza (sem tocar no BD)."""
    tr = tr.copy()
    tr["chave"] = tr["descricao"].map(C.chave_estabelecimento)
    agg = (
        tr.groupby("chave")
        .agg(
            nome_original=("descricao", "first"),
            categoria=("categoria", lambda s: s.value_counts().index[0]),
            categoria_id=("categoria_id", lambda s: s.value_counts().index[0]),
            qtd=("descricao", "size"),
        )
        .reset_index()
    )
    vecs = emb.encode(agg["chave"].tolist(), normalize_embeddings=False,
                      show_progress_bar=False)
    return agg, np.asarray(vecs)


def persistir_base_conhecimento(agg, vecs):
    """Popula a tabela `estabelecimentos` e a coleção PGVector (etapa que grava no BD)."""
    from sqlalchemy import text

    eng = C.engine_sync()
    with eng.begin() as cx:
        existentes = {
            r[0] for r in cx.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public'")).fetchall()
        }
        # DELETE (não TRUNCATE CASCADE) para nunca afetar `transacoes`
        cx.execute(text("UPDATE transacoes SET estabelecimento_id = NULL "
                        "WHERE estabelecimento_id IS NOT NULL"))
        for tbl in ("estabelecimento_aliases", "confirmacoes_categoria_marketplace",
                    "sugestoes_categoria_marketplace", "estabelecimentos"):
            if tbl in existentes:
                cx.execute(text(f"DELETE FROM {tbl}"))
        cx.execute(text("ALTER SEQUENCE estabelecimentos_id_seq RESTART WITH 1"))
        # remove QUALQUER coleção/embedding pré-existente (evita rótulos poluídos
        # por execuções anteriores do próprio agente via salvar_vectorstore)
        cx.execute(text("DELETE FROM langchain_pg_embedding"))
        cx.execute(text("DELETE FROM langchain_pg_collection"))
        cx.execute(text(
            "DELETE FROM langchain_pg_collection WHERE name = :n"), {"n": COLLECTION})
        cx.execute(text(
            "INSERT INTO langchain_pg_collection (uuid, name, cmetadata) "
            "VALUES (gen_random_uuid(), :n, '{}'::json) ON CONFLICT DO NOTHING"),
            {"n": COLLECTION})
        coll_uuid = cx.execute(
            text("SELECT uuid FROM langchain_pg_collection WHERE name=:n"),
            {"n": COLLECTION}).scalar()

        for (_, row), v in zip(agg.iterrows(), vecs):
            vlist = "[" + ",".join(f"{x:.7f}" for x in v.tolist()) + "]"
            cx.execute(text(
                "INSERT INTO estabelecimentos "
                "(nome_original, nome_normalizado, categoria_id, eh_marketplace, "
                " confianca, fonte, metadados, embedding, qtd_transacoes) "
                "VALUES (:no, :nn, :cid, false, 0.90, 'importacao', "
                " CAST(:md AS jsonb), CAST(:emb AS vector), :qtd)"),
                {"no": row["nome_original"], "nn": row["chave"],
                 "cid": int(row["categoria_id"]),
                 "md": f'{{"categoria": "{row["categoria"]}"}}',
                 "emb": vlist, "qtd": int(row["qtd"])})
            cx.execute(text(
                "INSERT INTO langchain_pg_embedding "
                "(id, collection_id, embedding, document, cmetadata) "
                "VALUES (gen_random_uuid(), :cid, CAST(:emb AS vector), :doc, "
                " CAST(:md AS jsonb))"),
                {"cid": coll_uuid, "emb": vlist, "doc": row["chave"],
                 "md": f'{{"categoria": "{row["categoria"]}", '
                       f'"categoria_id": {int(row["categoria_id"])}}}'})
    print(f"BD populado: {len(agg)} estabelecimentos + coleção PGVector '{COLLECTION}'")


def latencia_pgvector_real(test, emb, n=120):
    """Mede a latência real de uma consulta de similaridade no PGVector (índice + rede)."""
    from sqlalchemy import text

    amostra = test["descricao"].head(n).tolist()
    qs = emb.encode([C.chave_estabelecimento(d) for d in amostra], show_progress_bar=False)
    eng = C.engine_sync()
    lats = []
    with eng.connect() as cx:
        for v in qs:
            vlist = "[" + ",".join(f"{x:.7f}" for x in v.tolist()) + "]"
            t0 = time.perf_counter()
            cx.execute(text(
                "SELECT document, cmetadata, embedding <=> CAST(:q AS vector) AS dist "
                "FROM langchain_pg_embedding ORDER BY embedding <=> CAST(:q AS vector) "
                "LIMIT 3"), {"q": vlist}).fetchall()
            lats.append((time.perf_counter() - t0) * 1000.0)
    return float(np.mean(lats))


def classificar_knn(test, emb, base_vecs, base_cats):
    bn = base_vecs / (np.linalg.norm(base_vecs, axis=1, keepdims=True) + 1e-9)
    q = emb.encode([C.chave_estabelecimento(d) for d in test["descricao"]],
                   show_progress_bar=False)
    qn = q / (np.linalg.norm(q, axis=1, keepdims=True) + 1e-9)

    t0 = time.perf_counter()
    sims = qn @ bn.T
    lat = (time.perf_counter() - t0) / len(test) * 1000.0

    y_pred, top_sim = [], []
    for row in sims:
        idx = np.argsort(row)[::-1][:K]
        votos = defaultdict(float)
        for j in idx:
            votos[base_cats[j]] += float(row[j])
        y_pred.append(max(votos, key=votos.get))
        top_sim.append(float(row[idx[0]]))
    return y_pred, lat, np.array(top_sim)


def main(persistir: bool):
    tr, val, test = C.carregar_splits()
    emb = _embedder()
    agg, base_vecs = base_conhecimento(C.pd.concat([tr, val], ignore_index=True), emb)
    y_pred, _lat_np, top_sim = classificar_knn(test, emb, base_vecs, agg["categoria"].tolist())

    if persistir:
        persistir_base_conhecimento(agg, base_vecs)

    # latência = consulta real no PGVector (só disponível após popular o BD)
    try:
        lat = latencia_pgvector_real(test, emb)
    except Exception as e:  # noqa
        print(f"  (latência pgvector indisponível: {str(e)[:80]}) -> usando numpy")
        lat = _lat_np

    cobertura = float((top_sim >= LIMIAR).mean())
    C.registrar_resultado(
        "rag_pgvector_minilm",
        {"embedding_model": MODEL_NAME, "dim": 384, "k": K,
         "voto": "ponderado_cosseno", "limiar_alta_confianca": LIMIAR},
        test["categoria"].tolist(), y_pred, lat,
        tags={"familia": "rag_denso"},
        extra_metrics={"cobertura_alta_confianca": cobertura,
                       "similaridade_media_top1": float(top_sim.mean())},
    )
    print(f"cobertura sim>={LIMIAR}: {cobertura:.1%}  | latência pgvector: {lat:.2f} ms")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--persistir-bd", action="store_true",
                    help="grava a base de conhecimento em `estabelecimentos` + PGVector")
    a = ap.parse_args()
    main(persistir=a.persistir_bd)
