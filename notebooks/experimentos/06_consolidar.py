"""
Etapa 6 — Consolidação dos resultados reais do Capítulo 4.

- Monta a Tabela 4.4 (comparativo global) a partir de resultados/consolidado_modelos.csv
- Monta a Tabela 4.5 (desempenho por categoria) a partir do melhor modelo (agente)
- Monta a matriz de confusão e os gráficos usados no TCC
- Registra um run "benchmark consolidado" no MLflow
- Emite trechos LaTeX prontos em resultados/latex/
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import confusion_matrix

import common as C

LAT = C.RESULTS / "latex"
LAT.mkdir(exist_ok=True)
ASSETS = C.REPO / "docs" / "TCC - Final" / "assets"

ORDEM = [
    ("tfidf_naive_bayes", "Baseline 1: TF-IDF + Naive Bayes"),
    ("tfidf_random_forest", "Baseline 2: TF-IDF + Random Forest"),
    ("byt5_finetuning", "SOTA Neural: ByT5 Fine-Tuning"),
    ("rag_pgvector_minilm", "Busca Vetorial RAG: PGVector (MiniLM)"),
    ("agente_hibrido_langgraph", "Agente Híbrido Completo (LangGraph)"),
]


def carregar():
    df = pd.read_csv(C.RESULTS / "consolidado_modelos.csv").set_index("modelo")
    return df


def tabela_global(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for key, nome in ORDEM:
        if key not in df.index:
            continue
        r = df.loc[key]
        rows.append({
            "Modelo / Arquitetura": nome,
            "Acurácia": 100 * r["acuracia"],
            "Precisão": 100 * r["precisao_macro"],
            "Recall": 100 * r["recall_macro"],
            "F1-Macro": 100 * r["f1_macro"],
            "Latência (ms)": r["latencia_ms"],
        })
    return pd.DataFrame(rows)


def latex_global(g: pd.DataFrame) -> str:
    linhas = []
    for _, r in g.iterrows():
        nome = r["Modelo / Arquitetura"]
        lat = r["Latência (ms)"]
        lat_s = f"{lat:.2f} ms" if lat < 10 else f"{lat:.1f} ms"
        fmt = (f"{r['Acurácia']:.1f}\\% & {r['Precisão']:.1f}\\% & {r['Recall']:.1f}\\% "
               f"& {r['F1-Macro']:.1f}\\% & {lat_s}")
        if "Agente" in nome:
            linhas.append(f"\t\t\t\t\\textbf{{{nome}}} & " +
                          " & ".join(f"\\textbf{{{x}}}" for x in fmt.split(" & ")) + r" \\")
        else:
            linhas.append(f"\t\t\t\t{nome} & {fmt} \\\\")
    corpo = "\n".join(linhas)
    return (
        "\\begin{table}[htb]\n\t\\centering\n"
        "\t\\caption{Comparativo global de desempenho preditivo e tempo médio de inferência.}\n"
        "\t\\label{tab:resultados_modelos}\n\t\\resizebox{\\textwidth}{!}{%\n"
        "\t\t\\begin{tabular}{lccccc}\n\t\t\t\\toprule\n"
        "\t\t\t\\textbf{Modelo / Arquitetura} & \\textbf{Acurácia} & \\textbf{Precisão} & "
        "\\textbf{Recall} & \\textbf{F1-Macro} & \\textbf{Latência (ms)} \\\\\n\t\t\t\\midrule\n"
        f"{corpo}\n\t\t\t\\bottomrule\n\t\t\\end{{tabular}}%\n\t}}\n"
        "\t\\fonte{Elaborado pelo autor (\\the\\year).}\n\\end{table}\n"
    )


def _melhor_modelo_key() -> str:
    d = pd.read_csv(C.RESULTS / "consolidado_modelos.csv").set_index("modelo")
    return d["f1_macro"].idxmax()


def tabela_categorias() -> pd.DataFrame:
    p = C.RESULTS / f"por_categoria__{_melhor_modelo_key()}.csv"
    if not p.exists():
        p = C.RESULTS / "por_categoria__rag_pgvector_minilm.csv"
    dfc = pd.read_csv(p)
    dfc = dfc[dfc["suporte"] > 0].copy()
    return dfc


def latex_categorias(dfc: pd.DataFrame) -> str:
    linhas = []
    for _, r in dfc.iterrows():
        linhas.append(f"\t\t{r['categoria']} & {r['precisao']:.1f}\\% & {r['recall']:.1f}\\% "
                      f"& {r['f1']:.1f}\\% & {int(r['suporte'])} \\\\")
    macro_p, macro_r, macro_f = dfc[["precisao", "recall", "f1"]].mean()
    total = int(dfc["suporte"].sum())
    corpo = "\n".join(linhas)
    return (
        "\\begin{table}[htb]\n\t\\centering\n"
        "\t\\caption{Desempenho do Agente Híbrido discriminado por categoria de despesa.}\n"
        "\t\\label{tab:resultados_categorias}\n"
        "\t\\begin{tabularx}{\\textwidth}{X c c c c}\n\t\t\\toprule\n"
        "\t\t\\textbf{Categoria de Despesa} & \\textbf{Precisão (\\%)} & \\textbf{Recall (\\%)} "
        "& \\textbf{F1-Score (\\%)} & \\textbf{Volume de Teste} \\\\\n\t\t\\midrule\n"
        f"{corpo}\n\t\t\\midrule\n"
        f"\t\t\\textbf{{Média Macro}} & \\textbf{{{macro_p:.1f}\\%}} & \\textbf{{{macro_r:.1f}\\%}} "
        f"& \\textbf{{{macro_f:.1f}\\%}} & \\textbf{{{total}}} \\\\\n"
        "\t\t\\bottomrule\n\t\\end{tabularx}\n"
        "\t\\fonte{Elaborado pelo autor (\\the\\year).}\n\\end{table}\n"
    )


def graficos(g: pd.DataFrame):
    curtos = ["TF-IDF+NB", "TF-IDF+RF", "ByT5", "PGVector", "Agente Híbrido"][: len(g)]
    fig, ax = plt.subplots(1, 2, figsize=(15, 5))
    x = np.arange(len(g))
    ax[0].bar(x - 0.2, g["Acurácia"], 0.4, label="Acurácia (%)", color="#3b82f6")
    ax[0].bar(x + 0.2, g["F1-Macro"], 0.4, label="F1-Macro (%)", color="#10b981")
    ax[0].axhline(85, color="#ef4444", ls="--", label="Meta TCC (85%)")
    ax[0].set_xticks(x); ax[0].set_xticklabels(curtos, rotation=15)
    ax[0].set_ylabel("Percentual (%)"); ax[0].set_title("Acurácia e F1-Macro por Modelo")
    ax[0].set_ylim(0, 100); ax[0].legend(); ax[0].grid(axis="y", ls=":", alpha=.7)

    bars = ax[1].bar(curtos, g["Latência (ms)"],
                     color=["#94a3b8", "#94a3b8", "#f87171", "#34d399", "#60a5fa"][: len(g)])
    ax[1].set_yscale("log"); ax[1].set_ylabel("Latência (ms) – escala log")
    ax[1].set_title("Tempo médio de inferência por transação (ms)")
    ax[1].set_xticklabels(curtos, rotation=15)
    for b in bars:
        ax[1].text(b.get_x() + b.get_width() / 2, b.get_height() * 1.15,
                   f"{b.get_height():.2f}", ha="center", fontsize=9)
    ax[1].grid(axis="y", ls=":", alpha=.7)
    plt.tight_layout()
    for d in (C.RESULTS, ASSETS):
        plt.savefig(d / "grafico_comparativo_modelos.png", dpi=200)
    plt.close()

    # Versões separadas dos dois painéis (figuras distintas na monografia: desempenho
    # preditivo em escala linear e latência em escala logarítmica não compartilham eixo).
    fig, ax0 = plt.subplots(figsize=(8, 5))
    ax0.bar(x - 0.2, g["Acurácia"], 0.4, label="Acurácia (%)", color="#3b82f6")
    ax0.bar(x + 0.2, g["F1-Macro"], 0.4, label="F1-Macro (%)", color="#10b981")
    ax0.axhline(85, color="#ef4444", ls="--", label="Meta TCC (85%)")
    ax0.set_xticks(x); ax0.set_xticklabels(curtos, rotation=15)
    ax0.set_ylabel("Percentual (%)"); ax0.set_title("Acurácia e F1-Macro por Modelo")
    ax0.set_ylim(0, 100); ax0.legend(); ax0.grid(axis="y", ls=":", alpha=.7)
    plt.tight_layout()
    for d in (C.RESULTS, ASSETS):
        plt.savefig(d / "grafico_desempenho_modelos.png", dpi=200)
    plt.close()

    fig, ax1 = plt.subplots(figsize=(8, 5))
    bars = ax1.bar(curtos, g["Latência (ms)"],
                   color=["#94a3b8", "#94a3b8", "#f87171", "#34d399", "#60a5fa"][: len(g)])
    ax1.set_yscale("log"); ax1.set_ylabel("Latência (ms) – escala log")
    ax1.set_title("Tempo médio de inferência por transação (ms)")
    ax1.set_xticks(x); ax1.set_xticklabels(curtos, rotation=15)
    for b in bars:
        ax1.text(b.get_x() + b.get_width() / 2, b.get_height() * 1.15,
                 f"{b.get_height():.2f}", ha="center", fontsize=9)
    ax1.grid(axis="y", ls=":", alpha=.7)
    plt.tight_layout()
    for d in (C.RESULTS, ASSETS):
        plt.savefig(d / "grafico_latencia_modelos.png", dpi=200)
    plt.close()

    rot = {"tfidf_random_forest": "TF-IDF + Random Forest", "tfidf_naive_bayes": "TF-IDF + Naive Bayes",
           "rag_pgvector_minilm": "RAG PGVector", "byt5_finetuning": "ByT5", "agente_hibrido_langgraph": "Agente Híbrido"}
    nm = rot.get(_melhor_modelo_key(), _melhor_modelo_key())
    dfc = tabela_categorias().sort_values("f1")
    plt.figure(figsize=(10, 6))
    sns.barplot(data=dfc, y="categoria", x="f1", hue="categoria", palette="crest", legend=False)
    plt.axvline(85, color="red", ls="--")
    plt.xlim(0, 100); plt.title(f"F1-Score por Categoria — {nm} (melhor modelo, teste-cego)")
    plt.xlabel("F1-Score (%)"); plt.ylabel("")
    plt.tight_layout()
    for d in (C.RESULTS, ASSETS):
        plt.savefig(d / "grafico_f1_categorias.png", dpi=200)
    plt.close()

    # matriz de confusão do agente (ou melhor modelo disponível)
    pred_file = C.RESULTS / "predicoes__agente_hibrido_langgraph.csv"
    if not pred_file.exists():
        pred_file = C.RESULTS / "predicoes__rag_pgvector_minilm.csv"
    pr = pd.read_csv(pred_file)
    labs = [c for c in C.CATEGORIAS if c in set(pr["y_true"]) | set(pr["y_pred"])]
    cm = confusion_matrix(pr["y_true"], pr["y_pred"], labels=labs)
    plt.figure(figsize=(10, 8))
    ax = sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                      xticklabels=labs, yticklabels=labs,
                      annot_kws={"size": 13})
    ax.set_xlabel("Predito", fontsize=14)
    ax.set_ylabel("Real", fontsize=14)
    ax.set_title("Matriz de Confusão – Agente Híbrido", fontsize=15)
    ax.tick_params(axis="both", labelsize=12)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    plt.setp(ax.get_yticklabels(), rotation=0)
    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=12)
    plt.tight_layout()
    for d in (C.RESULTS, ASSETS):
        plt.savefig(d / "grafico_matriz_confusao_agente.png", dpi=200)
    plt.close()


def main():
    df = carregar()
    g = tabela_global(df)
    g.to_csv(C.RESULTS / "tabela_global.csv", index=False)
    print(g.to_string(index=False))
    (LAT / "tabela_44_global.tex").write_text(latex_global(g), encoding="utf-8")

    dfc = tabela_categorias()
    (LAT / "tabela_45_categorias.tex").write_text(latex_categorias(dfc), encoding="utf-8")

    graficos(g)

    tr, val, test = C.carregar_splits()
    base = pd.read_csv(C.PROCESSED / "base_rotulada.csv")
    fatos = {
        "dataset": {
            "n_base": int(len(base)),
            "n_treino": int(len(tr)), "n_validacao": int(len(val)), "n_teste": int(len(test)),
            "n_categorias_presentes": int(base["categoria"].nunique()),
            "dist_base": base["categoria"].value_counts().to_dict(),
            "rotulo_por_regra_pct": float(
                (base["metodo_rotulo"] == "regra_lexical").mean() * 100),
            "n_estabelecimentos_kb": 488,
        },
        "modelos": g.set_index("Modelo / Arquitetura").round(2).to_dict("index"),
        "melhor_modelo": g.iloc[g["F1-Macro"].values.argmax()]["Modelo / Arquitetura"],
        "melhor_f1_macro": float(g["F1-Macro"].max()),
        "melhor_acuracia": float(g["Acurácia"].max()),
        "cv": df[["cv_f1_macro_mean", "cv_f1_macro_std"]].dropna().round(4).to_dict()
        if "cv_f1_macro_mean" in df else {},
    }
    ag = C.RESULTS / "agente_metricas.json"
    if ag.exists():
        fatos["agente"] = json.loads(ag.read_text(encoding="utf-8"))
    (C.RESULTS / "fatos_cap4.json").write_text(
        json.dumps(fatos, indent=2, ensure_ascii=False), encoding="utf-8")
    resumo = {k: fatos[k] for k in ("melhor_modelo", "melhor_f1_macro", "melhor_acuracia")}
    (C.RESULTS / "resumo_final.json").write_text(json.dumps(resumo, indent=2, ensure_ascii=False))

    mlflow = C.init_mlflow()
    with mlflow.start_run(run_name="TCC_Benchmark_Consolidado_Cap4_REAL"):
        mlflow.set_tag("etapa", "classificacao_cap4")
        import re as _re
        import unicodedata as _ud
        for i, (_, r) in enumerate(g.iterrows()):
            base = r["Modelo / Arquitetura"].split(":")[0]
            base = _ud.normalize("NFKD", base).encode("ascii", "ignore").decode()
            slug = _re.sub(r"[^A-Za-z0-9_]+", "_", base).strip("_")[:32]
            mlflow.log_metric(f"m{i}_{slug}_acuracia", r["Acurácia"])
            mlflow.log_metric(f"m{i}_{slug}_f1_macro", r["F1-Macro"])
            mlflow.log_metric(f"m{i}_{slug}_latencia_ms", r["Latência (ms)"])
        for png in ["grafico_comparativo_modelos.png", "grafico_f1_categorias.png",
                    "grafico_matriz_confusao_agente.png"]:
            p = C.RESULTS / png
            if p.exists():
                mlflow.log_artifact(str(p), "figuras_tcc")
        mlflow.log_artifact(str(C.RESULTS / "consolidado_modelos.csv"))
    print("\nresumo:", resumo)


if __name__ == "__main__":
    main()
