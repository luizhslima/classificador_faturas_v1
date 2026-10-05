"""
Etapa 13 — Duas verificações complementares solicitadas na revisão de 21/09/2026.

(a) Efeito da extração sobre a classificação (C-02): o classificador TF-IDF + Random
    Forest (mesma configuração da etapa 02, treinado em treino+validação) é aplicado
    às 699 descrições da bateria de extração (data/c6_ocr_benchmark_transactions.csv)
    em três versões — descrição oficial do CSV, descrição extraída pelo Docling V2 e
    descrição transcrita pelo Tesseract — e mede-se a concordância entre a categoria
    atribuída ao texto extraído e a atribuída ao texto oficial.

(b) Testes de McNemar adicionais (M-15c): agente híbrido versus as duas melhores
    arquiteturas (TF-IDF + Random Forest e busca vetorial densa com normalização),
    e correção de Bonferroni para os seis testes binomiais da Tabela de acurácia.

Saída: resultados/classificacao_pos_extracao.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline

import common as C

RES = C.RESULTADOS if hasattr(C, "RESULTADOS") else (C.REPO / "notebooks" / "experimentos" / "resultados")


def _features():
    return ColumnTransformer(
        [
            ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=1,
                                     sublinear_tf=True), "descricao"),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=1),
             "descricao"),
        ]
    )


def mcnemar(a_ok: np.ndarray, b_ok: np.ndarray) -> dict:
    b = int(((a_ok) & (~b_ok)).sum())   # só A acerta
    c = int(((~a_ok) & (b_ok)).sum())   # só B acerta
    both = int((a_ok & b_ok).sum())
    none = int((~a_ok & ~b_ok).sum())
    if b + c == 0:
        chi2, p = 0.0, 1.0
    else:
        chi2 = (abs(b - c) - 1) ** 2 / (b + c)
        p = float(stats.chi2.sf(chi2, df=1))
    return {"ambos_acertam": both, "ambos_erram": none, "so_A": b, "so_B": c,
            "chi2": round(float(chi2), 3), "p": round(p, 4)}


def parte_a() -> dict:
    tr, val, _ = C.carregar_splits()
    dev = pd.concat([tr, val], ignore_index=True)
    pipe = Pipeline([("feat", _features()),
                     ("clf", RandomForestClassifier(n_estimators=400, random_state=C.RANDOM_STATE,
                                                    n_jobs=-1, class_weight="balanced_subsample"))])
    pipe.fit(dev[["descricao"]], dev["categoria"])

    bench = pd.read_csv(C.REPO / "data" / "c6_ocr_benchmark_transactions.csv")
    bench["gt_description"] = bench["gt_description"].astype(str)
    bench["pred_description"] = bench["pred_description"].fillna("").astype(str)
    out = {"n_transacoes_por_metodo": {}, "concordancia": {}, "concordancia_exatas": {},
           "concordancia_nao_exatas": {}}
    for metodo, g in bench.groupby("method"):
        y_ref = pipe.predict(g[["gt_description"]].rename(columns={"gt_description": "descricao"}))
        y_hyp = pipe.predict(g[["pred_description"]].rename(columns={"pred_description": "descricao"}))
        iguais = (y_ref == y_hyp)
        exact = g["is_exact"].astype(bool).to_numpy()
        out["n_transacoes_por_metodo"][metodo] = int(len(g))
        out["concordancia"][metodo] = round(float(iguais.mean()) * 100, 1)
        out["concordancia_exatas"][metodo] = round(float(iguais[exact].mean()) * 100, 1) if exact.any() else None
        out["concordancia_nao_exatas"][metodo] = round(float(iguais[~exact].mean()) * 100, 1) if (~exact).any() else None
        out.setdefault("n_nao_exatas", {})[metodo] = int((~exact).sum())
    # também: classe atribuída ao texto do CSV é usada como referência; quantas descrições
    # do CSV coincidem com estabelecimentos do conjunto de treino (memorização)?
    chaves_dev = set(dev["descricao"].map(C.chave_estabelecimento))
    ref_desc = bench[bench["method"] == "Docling"]["gt_description"]
    out["fracao_descricoes_csv_vistas_no_treino"] = round(
        float(ref_desc.map(C.chave_estabelecimento).isin(chaves_dev).mean()) * 100, 1)
    return out


def parte_b() -> dict:
    def ok(nome):
        d = pd.read_csv(RES / f"predicoes__{nome}.csv")
        return (d["y_true"] == d["y_pred"]).to_numpy()
    ag = ok("agente_hibrido_langgraph")
    rf = ok("tfidf_random_forest")
    rag = ok("rag_pgvector_minilm_norm")
    nb = ok("tfidf_naive_bayes")
    res = {
        "mcnemar_rf_vs_agente": mcnemar(rf, ag),
        "mcnemar_ragnorm_vs_agente": mcnemar(rag, ag),
        "mcnemar_nb_vs_agente": mcnemar(nb, ag),
    }
    # Bonferroni para os seis testes binomiais (Tabela de acurácia)
    n = 334
    p_nb = float(stats.binomtest(int(nb.sum()), n, 0.85, alternative="greater").pvalue)
    res["binomial_nb_p"] = round(p_nb, 4)
    res["bonferroni_alpha_6_testes"] = round(0.05 / 6, 4)
    res["nb_significativo_apos_bonferroni"] = bool(p_nb < 0.05 / 6)
    return res


if __name__ == "__main__":
    resultado = {"parte_a_extracao_vs_classificacao": parte_a(), "parte_b_mcnemar_adicional": parte_b()}
    (RES / "classificacao_pos_extracao.json").write_text(json.dumps(resultado, indent=2, ensure_ascii=False),
                                                         encoding="utf-8")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
