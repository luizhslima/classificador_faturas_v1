"""
Etapa 11 — Intervalo de confiança e teste exato para a ACURÁCIA GLOBAL (verificação de H1a).

O Capítulo 5 aplica bootstrap e McNemar ao F1-Macro (etapa 09). Esta etapa completa o
protocolo para a acurácia global — a métrica da subhipótese H1a — com:

  (i)  intervalo de confiança de 95% de Wilson para a proporção de acertos (k/n);
  (ii) teste binomial exato unilateral, H0: acurácia <= 85% contra H1: acurácia > 85%.

Também contabiliza, a partir de resultados/agente_teste_bruto.csv, quantas predições do
agente na classe residual "Despesas Diversas / Outros" foram produzidas pelo ancoramento
externo (05_agente._ancorar) e não pelo próprio rótulo devolvido pelo grafo, além das
métricas da execução complementar com a ferramenta de busca web (agente_teste_bruto_COMWEB.csv).

Saída: resultados/ic_acuracia.json
"""
from __future__ import annotations

import json
from math import sqrt

import numpy as np
from scipy.stats import binomtest
from sklearn.metrics import f1_score

import common as C

LIMIAR = 0.85
Z = 1.959964  # quantil 97,5% da normal padrão
RESIDUAL = "Despesas Diversas / Outros"


def wilson(k: int, n: int, z: float = Z) -> tuple[float, float]:
    p = k / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    meia = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centro - meia, centro + meia


def main():
    out = {"limiar": LIMIAR, "acuracia_por_arquitetura": {}}
    for p in sorted(C.RESULTS.glob("predicoes__*.csv")):
        d = C.pd.read_csv(p)
        k = int((d["y_true"] == d["y_pred"]).sum())
        n = int(len(d))
        lo, hi = wilson(k, n)
        out["acuracia_por_arquitetura"][p.stem.replace("predicoes__", "")] = {
            "acertos": k, "n": n, "acuracia": k / n,
            "ic95_wilson": [lo, hi],
            "p_binomial_unilateral_h0_menor_igual_85": float(
                binomtest(k, n, LIMIAR, alternative="greater").pvalue),
        }

    bruto = C.RESULTS / "agente_teste_bruto.csv"
    if bruto.exists():
        a = C.pd.read_csv(bruto)
        dd = a[a["y_pred"] == RESIDUAL]
        out["agente_residual"] = {
            "n_pred_residual": int(len(dd)),
            "n_ja_residual_no_rotulo_do_grafo": int((dd["categoria"] == RESIDUAL).sum()),
            "n_atribuidas_pelo_ancoramento_externo": int((dd["categoria"] != RESIDUAL).sum()),
            "por_fonte": dd["fonte"].value_counts().to_dict(),
        }
        llm = a[a["fonte"].isin(["llm", "humano"])]
        vet = a[a["fonte"] == "vetorial"]
        out["agente_latencia_condicional_ms"] = {
            "ramo_llm_media": float(llm["lat_ms"].mean()),
            "ramo_llm_mediana": float(llm["lat_ms"].median()),
            "ramo_vetorial_media": float(vet["lat_ms"].mean()),
            "global_media": float(a["lat_ms"].mean()),
        }

    comweb = C.RESULTS / "agente_teste_bruto_COMWEB.csv"
    if comweb.exists():
        c = C.pd.read_csv(comweb)
        labels = sorted(set(c["y_true"]))
        out["agente_com_busca_web"] = {
            "n": int(len(c)),
            "acuracia": float((c["y_pred"] == c["y_true"]).mean()),
            "f1_macro": float(f1_score(c["y_true"], c["y_pred"], average="macro",
                                       labels=labels, zero_division=0)),
            "erros_execucao": int(c["erro"].notna().sum()) if "erro" in c else 0,
            "por_fonte": c["fonte"].value_counts(dropna=False).rename(lambda x: str(x)).to_dict(),
            "hitl": int(c["hitl"].sum()),
            "latencia_ms_media": float(c["lat_ms"].mean()),
        }

    (C.RESULTS / "ic_acuracia.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
