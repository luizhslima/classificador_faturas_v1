"""
Etapa 12 — Regeneração das figuras do Capítulo 5 em conformidade com a revisão de 19/09/2026.

Gera, em resultados/ e em docs/TCC - Final/assets/:
  * grafico_distribuicao_cer_wer.png   — Figura 3 (boxplot CER/WER, Docling V2 x Tesseract)
  * grafico_evolucao_cer_faturas.png   — Figura 4 (CER por competência, eixo em ordem cronológica)
  * grafico_exato_levenshtein_ocr.png  — Figura 5 (casamento exato e Levenshtein, painéis empilhados)
  * grafico_desempenho_modelos.png     — Figura 6 (acurácia e F1-Macro; linha "Limiar da hipótese (85%)")
  * grafico_latencia_modelos.png       — Figura 7 (latência, escala log)
  * grafico_f1_categorias.png          — Figura 8 (F1 por categoria do melhor modelo)
  * grafico_matriz_confusao_agente.png — Figura 9 (matriz de confusão do agente)

Regras aplicadas: sem título interno (a legenda ABNT identifica a ilustração); rótulos de
arquitetura idênticos aos das tabelas do capítulo; fontes ampliadas; competências ordenadas.
Fonte dos dados: data/c6_ocr_benchmark_summary.csv (bateria de extração, gerada por
notebooks/data_analysis.ipynb) e resultados/*.csv (etapas 02 a 05).
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import confusion_matrix

import common as C

ASSETS = C.REPO / "docs" / "TCC - Final" / "assets"
VERDE, VERMELHO = "#2ecc71", "#e74c3c"
ROTULOS = {
    "tfidf_naive_bayes": "TF-IDF +\nNaive Bayes",
    "tfidf_random_forest": "TF-IDF +\nRandom Forest",
    "byt5_finetuning": "ByT5 com\najuste fino",
    "rag_pgvector_minilm": "Busca vetorial\ndensa (pgvector)",
    "agente_hibrido_langgraph": "Agente Híbrido\n(LangGraph)",
}
ORDEM = list(ROTULOS)

sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams.update({"font.size": 13, "axes.labelsize": 14, "xtick.labelsize": 12,
                     "ytick.labelsize": 12, "legend.fontsize": 12})


def _save(fig, nome):
    fig.tight_layout()
    for d in (C.RESULTS, ASSETS):
        fig.savefig(d / nome, dpi=200)
    plt.close(fig)
    print("gerado:", nome)


# ---------------------------------------------------------------- OCR (Figuras 3 a 5)
def figuras_ocr():
    df = pd.read_csv(C.DATA / "c6_ocr_benchmark_summary.csv")
    df = df.sort_values("invoice").reset_index(drop=True)  # ordem cronológica AAAA-MM
    n = len(df)
    x = np.arange(n)
    w = 0.38

    # Figura 3 — distribuição de CER e WER
    box = pd.DataFrame({
        "Valor": list(df["docling_full_cer"]) + list(df["tess_full_cer"])
                 + list(df["docling_full_wer"]) + list(df["tess_full_wer"]),
        "Métrica": ["CER"] * (2 * n) + ["WER"] * (2 * n),
        "Motor": (["Docling V2"] * n + ["Tesseract"] * n) * 2,
    })
    fig, ax = plt.subplots(figsize=(9, 6))
    sns.boxplot(data=box, x="Métrica", y="Valor", hue="Motor", ax=ax, palette=[VERDE, VERMELHO])
    ax.set_ylabel("Taxa de erro por transação (0 = transcrição perfeita)")
    ax.set_xlabel("")
    ax.set_ylim(-0.05, 1.25)
    ax.legend(title="")
    _save(fig, "grafico_distribuicao_cer_wer.png")

    # Figura 4 — CER por competência
    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.bar(x - w / 2, df["docling_full_cer"] * 100, w, label="Docling V2", color=VERDE)
    ax.bar(x + w / 2, df["tess_full_cer"] * 100, w, label="Tesseract", color=VERMELHO)
    ax.set_xticks(x)
    ax.set_xticklabels(df["invoice"], rotation=45, ha="right", fontsize=13)
    ax.set_ylabel("CER (%)")
    ax.set_xlabel("Competência da fatura (ano-mês)")
    ax.legend()
    _save(fig, "grafico_evolucao_cer_faturas.png")

    # Figura 5 — casamento exato e Levenshtein, empilhados
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    a1.bar(x - w / 2, df["docling_exact_rate"] * 100, w, label="Docling V2", color=VERDE)
    a1.bar(x + w / 2, df["tess_exact_rate"] * 100, w, label="Tesseract", color=VERMELHO)
    a1.set_ylabel("Casamento exato (%)")
    a1.legend()
    a2.bar(x - w / 2, df["docling_full_lev"], w, label="Docling V2", color=VERDE)
    a2.bar(x + w / 2, df["tess_full_lev"], w, label="Tesseract", color=VERMELHO)
    a2.set_ylabel("Distância de Levenshtein média\n(operações por transação)")
    a2.set_xlabel("Competência da fatura (ano-mês)")
    a2.set_xticks(x)
    a2.set_xticklabels(df["invoice"], rotation=45, ha="right", fontsize=13)
    a2.legend()
    _save(fig, "grafico_exato_levenshtein_ocr.png")


# ---------------------------------------------------------------- Classificação (Figuras 6 a 9)
def figuras_classificacao():
    cons = pd.read_csv(C.RESULTS / "consolidado_modelos.csv").set_index("modelo").loc[ORDEM]
    rot = [ROTULOS[m] for m in ORDEM]
    x = np.arange(len(ORDEM))

    # Figura 6 — acurácia e F1-Macro
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x - 0.2, 100 * cons["acuracia"], 0.4, label="Acurácia (%)", color="#3b82f6")
    ax.bar(x + 0.2, 100 * cons["f1_macro"], 0.4, label="F1-Macro (%)", color="#10b981")
    ax.axhline(85, color="#ef4444", ls="--", label="Limiar da hipótese (85%)")
    ax.set_xticks(x)
    ax.set_xticklabels(rot)
    ax.set_ylabel("Percentual (%)")
    ax.set_ylim(0, 100)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, frameon=False)
    ax.grid(axis="y", ls=":", alpha=.7)
    _save(fig, "grafico_desempenho_modelos.png")

    # Figura 7 — latência (log)
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(x, cons["latencia_ms"], color=["#94a3b8", "#94a3b8", "#f87171", "#34d399", "#60a5fa"])
    ax.set_yscale("log")
    ax.set_ylabel("Latência média por transação (ms, escala logarítmica)")
    ax.set_xticks(x)
    ax.set_xticklabels(rot)
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() * 1.18, f"{b.get_height():.2f}",
                ha="center", fontsize=12)
    ax.grid(axis="y", ls=":", alpha=.7)
    _save(fig, "grafico_latencia_modelos.png")

    # Figura 8 — F1 por categoria do melhor modelo (F1-Macro)
    melhor = cons["f1_macro"].idxmax()
    dfc = pd.read_csv(C.RESULTS / f"por_categoria__{melhor}.csv")
    dfc = dfc[dfc["suporte"] > 0].sort_values("f1").copy()
    dfc["rotulo"] = [f"{c} (n = {int(s)})" for c, s in zip(dfc["categoria"], dfc["suporte"])]
    fig, ax = plt.subplots(figsize=(10.5, 6.5))
    sns.barplot(data=dfc, y="rotulo", x="f1", hue="rotulo", palette="crest", legend=False, ax=ax)
    ax.axvline(85, color="#ef4444", ls="--", label="Limiar da hipótese (85%)")
    for i, (_, r) in enumerate(dfc.iterrows()):
        ax.text(r["f1"] + 1.0, i, f"{r['f1']:.1f}".replace(".", ","), va="center", fontsize=11, color="#374151")
    ax.set_xlim(0, 112)
    ax.set_xticks(range(0, 101, 20))
    ax.set_xlabel("F1-Score (%); n = volume de teste da categoria")
    ax.set_ylabel("")
    ax.legend(loc="upper left", bbox_to_anchor=(0.12, 0.99), framealpha=1.0)
    _save(fig, "grafico_f1_categorias.png")

    # Figura 9 — matriz de confusão do agente
    pr = pd.read_csv(C.RESULTS / "predicoes__agente_hibrido_langgraph.csv")
    labs = [c for c in C.CATEGORIAS if c in set(pr["y_true"]) | set(pr["y_pred"])]
    cm = confusion_matrix(pr["y_true"], pr["y_pred"], labels=labs)
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=labs, yticklabels=labs,
                annot_kws={"size": 13}, ax=ax)
    ax.set_xlabel("Categoria predita", fontsize=14)
    ax.set_ylabel("Categoria real", fontsize=14)
    ax.tick_params(axis="both", labelsize=12)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    plt.setp(ax.get_yticklabels(), rotation=0)
    _save(fig, "grafico_matriz_confusao_agente.png")


if __name__ == "__main__":
    figuras_ocr()
    figuras_classificacao()
