"""
Etapa 9 — Busca vetorial RAG COM normalização léxica: predições, IC bootstrap e McNemar.

A ablação (etapa 7) reporta apenas o F1-Macro agregado da busca vetorial com
normalização léxica (66,8%), sem persistir as predições por transação. Esta etapa
reexecuta exatamente a mesma configuração (mesmo modelo de embedding, mesma base
treino+validação, mesmo k=3 ponderado por similaridade) e persiste as predições em
resultados/predicoes__rag_pgvector_minilm_norm.csv, para permitir:

  (i)  intervalo de confiança de 95% do F1-Macro por bootstrap percentil (B=2000, seed=42),
       com o mesmo procedimento aplicado às demais arquiteturas (Seção 5.4.2);
  (ii) teste de McNemar pareado (com correção de continuidade) entre esta configuração
       e o TF-IDF + Random Forest (melhor configuração de cada família de representação).

Saída: resultados/rag_norm_significancia.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
from scipy.stats import chi2
from sklearn.metrics import f1_score

import common as C

sys.path.insert(0, str(C.REPO / "notebooks" / "modules"))
from utils import normalizar_nome  # noqa: E402

B = 2000
SEED = 42


def rag_knn_norm(dev, test):
    """Cópia fiel de 07_ablacao.rag_knn(usar_norm=True), devolvendo as predições."""
    from sentence_transformers import SentenceTransformer
    emb = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", device="cpu")
    f = lambda s: normalizar_nome(str(s))  # noqa: E731
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
    return pred


def bootstrap_f1(y_true, y_pred, labels):
    rng = np.random.default_rng(SEED)
    y_true = np.asarray(y_true); y_pred = np.asarray(y_pred)
    n = len(y_true); vals = []
    for _ in range(B):
        idx = rng.integers(0, n, n)
        vals.append(f1_score(y_true[idx], y_pred[idx], average="macro",
                             labels=labels, zero_division=0))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def mcnemar(y_true, pa, pb):
    y_true = np.asarray(y_true); pa = np.asarray(pa); pb = np.asarray(pb)
    a_ok = pa == y_true; b_ok = pb == y_true
    both = int((a_ok & b_ok).sum()); neither = int((~a_ok & ~b_ok).sum())
    only_a = int((a_ok & ~b_ok).sum()); only_b = int((~a_ok & b_ok).sum())
    stat = (abs(only_a - only_b) - 1) ** 2 / (only_a + only_b) if (only_a + only_b) else 0.0
    return {"ambos_acertam": both, "ambos_erram": neither, "so_A": only_a, "so_B": only_b,
            "chi2": float(stat), "p": float(chi2.sf(stat, 1))}


def main():
    tr, val, test = C.carregar_splits()
    dev = C.pd.concat([tr, val], ignore_index=True)
    y_true = test["categoria"].tolist()
    labels = sorted(set(y_true))

    pred_norm = rag_knn_norm(dev, test)
    C.pd.DataFrame({"y_true": y_true, "y_pred": pred_norm}).to_csv(
        C.RESULTS / "predicoes__rag_pgvector_minilm_norm.csv", index=False)

    rf = C.pd.read_csv(C.RESULTS / "predicoes__tfidf_random_forest.csv")
    assert rf["y_true"].tolist() == y_true, "ordem do teste-cego divergente"

    # IC bootstrap de todas as arquiteturas (Tabela de IC do Cap. 5), mesmo gerador e semente
    ics = {}
    for p in sorted(C.RESULTS.glob("predicoes__*.csv")):
        d = C.pd.read_csv(p)
        assert d["y_true"].tolist() == y_true, f"ordem do teste-cego divergente em {p.name}"
        ics[p.stem.replace("predicoes__", "")] = {
            "f1_macro": float(f1_score(y_true, d["y_pred"], average="macro", labels=labels, zero_division=0)),
            "acuracia": float(np.mean(d["y_pred"].values == np.asarray(y_true))),
            "ic95_f1_macro": bootstrap_f1(y_true, d["y_pred"].tolist(), labels),
        }

    out = {
        "ic95_por_arquitetura": ics,
        "mcnemar_rf_vs_rag_norm": mcnemar(y_true, rf["y_pred"].tolist(), pred_norm),
        "mcnemar_rf_vs_nb": mcnemar(y_true, rf["y_pred"].tolist(),
                                    C.pd.read_csv(C.RESULTS / "predicoes__tfidf_naive_bayes.csv")["y_pred"].tolist()),
        "B": B, "seed": SEED,
    }
    (C.RESULTS / "rag_norm_significancia.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
