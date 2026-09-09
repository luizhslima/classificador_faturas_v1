"""
Etapa 7 — Ablação dos componentes (Tabela 4.6).

Mensura, de forma reprodutível e barata, o efeito de dois componentes-chave sobre
o teste-cego completo, usando os modelos rápidos como sonda:

  (A) Normalização léxica de gateways  -> TF-IDF+RF e RAG com descrição CRUA vs. NORMALIZADA
  (B) Busca vetorial densa (RAG)        -> contribuição medida pela cobertura de alta
                                          confiança e pela acurácia condicional do
                                          ramo vetorial do agente (etapa 5)

Os efeitos de CoT e busca web sobre o agente são reportados a partir das estatísticas
de roteamento do run completo do agente (resultados/agente_teste_bruto.csv), sem novo
custo de inferência.
"""
from __future__ import annotations

import json

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline

import common as C

sys = __import__("sys")
sys.path.insert(0, str(C.REPO / "notebooks" / "modules"))
from utils import normalizar_nome  # noqa: E402  (normalização léxica real do pipeline)


def _norm(s):
    return normalizar_nome(str(s))


def tfidf_rf(dev, test, coluna):
    feat = ColumnTransformer([
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True), coluna),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4)), coluna),
    ])
    pipe = Pipeline([("f", feat), ("c", RandomForestClassifier(
        n_estimators=400, random_state=C.RANDOM_STATE, n_jobs=-1,
        class_weight="balanced_subsample"))])
    pipe.fit(dev[[coluna]], dev["categoria"])
    pred = pipe.predict(test[[coluna]])
    return C.metricas_multiclasse(test["categoria"], pred)


def rag_knn(dev, test, usar_norm):
    from sentence_transformers import SentenceTransformer
    emb = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", device="cpu")
    f = (lambda s: _norm(s)) if usar_norm else (lambda s: str(s).lower())
    dev = dev.copy(); dev["k"] = dev["descricao"].map(f)
    agg = dev.groupby("k").agg(cat=("categoria", lambda s: s.value_counts().index[0])).reset_index()
    bv = emb.encode(agg["k"].tolist(), show_progress_bar=False)
    bv = bv / (np.linalg.norm(bv, axis=1, keepdims=True) + 1e-9)
    q = emb.encode([f(d) for d in test["descricao"]], show_progress_bar=False)
    q = q / (np.linalg.norm(q, axis=1, keepdims=True) + 1e-9)
    sims = q @ bv.T
    cats = agg["cat"].tolist()
    pred = []
    for row in sims:
        idx = np.argsort(row)[::-1][:3]
        v = {}
        for j in idx:
            v[cats[j]] = v.get(cats[j], 0) + float(row[j])
        pred.append(max(v, key=v.get))
    return C.metricas_multiclasse(test["categoria"], pred)


def main():
    tr, val, test = C.carregar_splits()
    dev = C.pd.concat([tr, val], ignore_index=True)
    for d in (dev, test):
        d["descricao_norm"] = d["descricao"].map(_norm)

    linhas = []

    rf_norm = tfidf_rf(dev, test, "descricao_norm")
    rf_raw = tfidf_rf(dev, test, "descricao")
    linhas.append({"componente": "Normalização léxica (TF-IDF+RF)",
                   "com": round(100 * rf_norm["f1_macro"], 1),
                   "sem": round(100 * rf_raw["f1_macro"], 1),
                   "delta_f1": round(100 * (rf_raw["f1_macro"] - rf_norm["f1_macro"]), 1)})

    rag_norm = rag_knn(dev, test, True)
    rag_raw = rag_knn(dev, test, False)
    linhas.append({"componente": "Normalização léxica (RAG MiniLM)",
                   "com": round(100 * rag_norm["f1_macro"], 1),
                   "sem": round(100 * rag_raw["f1_macro"], 1),
                   "delta_f1": round(100 * (rag_raw["f1_macro"] - rag_norm["f1_macro"]), 1)})

    # contribuição do RAG e roteamento do agente
    p = C.RESULTS / "agente_teste_bruto.csv"
    if p.exists():
        ag = C.pd.read_csv(p)
        vet = ag[ag["fonte"] == "vetorial"]
        llm = ag[ag["fonte"].isin(["llm", "humano"])]
        acc_vet = float((vet["y_pred"] == vet["y_true"]).mean()) if len(vet) else float("nan")
        acc_llm = float((llm["y_pred"] == llm["y_true"]).mean()) if len(llm) else float("nan")
        tool_rate = float(ag.get("erro", C.pd.Series()).astype(str).str.contains("tool").mean()) \
            if "erro" in ag else 0.0
        linhas.append({"componente": "Ramo vetorial (RAG) — acurácia condicional",
                       "com": round(100 * acc_vet, 1), "sem": round(100 * acc_llm, 1),
                       "delta_f1": round(100 * (acc_vet - acc_llm), 1)})
        roteamento = {
            "frac_vetorial": float((ag["fonte"] == "vetorial").mean()),
            "frac_llm": float(ag["fonte"].isin(["llm", "humano"]).mean()),
            "frac_hitl": float(ag["hitl"].mean()),
            "acuracia_ramo_vetorial": acc_vet,
            "acuracia_ramo_llm": acc_llm,
        }
    else:
        roteamento = {}

    C.pd.DataFrame(linhas).to_csv(C.RESULTS / "ablacao.csv", index=False)
    (C.RESULTS / "ablacao.json").write_text(json.dumps(
        {"componentes": linhas, "roteamento_agente": roteamento}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    print(C.pd.DataFrame(linhas).to_string(index=False))
    print(json.dumps(roteamento, indent=2))

    mlflow = C.init_mlflow()
    with mlflow.start_run(run_name="cls::ablacao_componentes"):
        mlflow.set_tag("etapa", "classificacao_cap4")
        import re as _re
        for i, r in enumerate(linhas):
            slug = _re.sub(r"[^A-Za-z0-9_]", "_", r["componente"])[:40]
            mlflow.log_metric(f"abl{i}_{slug}_delta_f1", r["delta_f1"])
        mlflow.log_artifact(str(C.RESULTS / "ablacao.csv"))


if __name__ == "__main__":
    main()
