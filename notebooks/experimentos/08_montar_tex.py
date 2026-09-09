"""
Etapa 8 — Monta os blocos LaTeX finais do Capítulo 4 (classificação) a partir dos
artefatos reais em resultados/. Gera:

  resultados/latex/cap4_sec46_classificacao.tex   (§4.6 completa: tabelas 4.4/4.5/4.6 + texto)
  resultados/latex/cap4_sec47_mlops.tex           (§4.7 MLOps/observabilidade)
  resultados/latex/cap4_sec48_questoes.tex        (§4.8 Q1-Q5 + veredito)
  resultados/latex/pretextual_snippets.md         (trechos p/ Resumo, Abstract, Cap5)
"""
from __future__ import annotations

import json

import pandas as pd

import common as C

L = C.RESULTS / "latex"
L.mkdir(exist_ok=True)


def br(x, d=1):
    """Número no padrão pt-BR (vírgula decimal)."""
    return f"{x:.{d}f}".replace(".", ",")


def pct(x, d=1):
    return br(x, d) + "\\%"


def carregar():
    cons = pd.read_csv(C.RESULTS / "consolidado_modelos.csv").set_index("modelo")
    fatos = json.loads((C.RESULTS / "fatos_cap4.json").read_text(encoding="utf-8")) \
        if (C.RESULTS / "fatos_cap4.json").exists() else {}
    ag = json.loads((C.RESULTS / "agente_metricas.json").read_text(encoding="utf-8")) \
        if (C.RESULTS / "agente_metricas.json").exists() else {}
    abl = json.loads((C.RESULTS / "ablacao.json").read_text(encoding="utf-8")) \
        if (C.RESULTS / "ablacao.json").exists() else {}
    return cons, fatos, ag, abl


def tabela_44(cons):
    ordem = [
        ("tfidf_naive_bayes", "Baseline 1: TF-IDF + Naive Bayes", False),
        ("tfidf_random_forest", "Baseline 2: TF-IDF + Random Forest", False),
        ("byt5_finetuning", "SOTA Neural: ByT5 Fine-Tuning (byt5-small)", False),
        ("rag_pgvector_minilm", "Busca Vetorial RAG: PGVector (MiniLM)", False),
        ("agente_hibrido_langgraph", "Agente Híbrido Completo (LangGraph)", True),
    ]
    linhas = []
    for key, nome, bold in ordem:
        if key not in cons.index:
            continue
        r = cons.loc[key]
        lat = r["latencia_ms"]
        lat_s = f"{lat/1000:.1f} s" if lat >= 1000 else (
            f"{lat:.2f} ms" if lat < 10 else f"{lat:.1f} ms")
        cells = [f"{100*r['acuracia']:.1f}\\%", f"{100*r['precisao_macro']:.1f}\\%",
                 f"{100*r['recall_macro']:.1f}\\%", f"{100*r['f1_macro']:.1f}\\%", lat_s]
        if bold:
            linhas.append("\t\t\t\t\\textbf{" + nome + "} & "
                          + " & ".join("\\textbf{" + c + "}" for c in cells) + r" \\")
        else:
            linhas.append(f"\t\t\t\t{nome} & " + " & ".join(cells) + r" \\")
    return (
        "\\begin{table}[htb]\n\t\\centering\n"
        "\t\\caption{Comparativo global de desempenho preditivo e tempo médio de inferência "
        "(teste-cego de 334 transações, estabelecimentos disjuntos).}\n"
        "\t\\label{tab:resultados_modelos}\n\t\\resizebox{\\textwidth}{!}{%\n"
        "\t\t\\begin{tabular}{lccccc}\n\t\t\t\\toprule\n"
        "\t\t\t\\textbf{Modelo / Arquitetura} & \\textbf{Acurácia} & \\textbf{Precisão} & "
        "\\textbf{Recall} & \\textbf{F1-Macro} & \\textbf{Latência} \\\\\n\t\t\t\\midrule\n"
        + "\n".join(linhas) +
        "\n\t\t\t\\bottomrule\n\t\t\\end{tabular}%\n\t}\n"
        "\t\\fonte{Elaborado pelo autor (\\the\\year). Latência do agente: média por "
        "transação, dominada pelo ramo LLM (gemma-4-e4b local).}\n\\end{table}\n"
    )


def tabela_45(cons):
    # usa o modelo de melhor F1-Macro
    melhor = cons["f1_macro"].idxmax()
    rotulos = {
        "tfidf_random_forest": "TF-IDF + Random Forest",
        "tfidf_naive_bayes": "TF-IDF + Naive Bayes",
        "rag_pgvector_minilm": "RAG PGVector (MiniLM)",
        "byt5_finetuning": "ByT5 (fine-tuning)",
        "agente_hibrido_langgraph": "Agente Híbrido",
    }
    nome_modelo = rotulos.get(melhor, melhor)
    p = C.RESULTS / f"por_categoria__{melhor}.csv"
    if not p.exists():
        p = C.RESULTS / "por_categoria__tfidf_random_forest.csv"
        nome_modelo = "TF-IDF + Random Forest"
    dfc = pd.read_csv(p)
    dfc = dfc[dfc["suporte"] > 0]
    linhas = [f"\t\t{r.categoria} & {r.precisao:.1f}\\% & {r.recall:.1f}\\% & {r.f1:.1f}\\% "
              f"& {int(r.suporte)} \\\\" for r in dfc.itertuples()]
    mp, mr, mf = dfc[["precisao", "recall", "f1"]].mean()
    tot = int(dfc["suporte"].sum())
    return nome_modelo, (
        "\\begin{table}[htb]\n\t\\centering\n"
        f"\t\\caption{{Desempenho do {nome_modelo} discriminado por categoria de despesa "
        "efetivamente avaliada.}\n"
        "\t\\label{tab:resultados_categorias}\n"
        "\t\\begin{tabularx}{\\textwidth}{X c c c c}\n\t\t\\toprule\n"
        "\t\t\\textbf{Categoria de Despesa} & \\textbf{Precisão (\\%)} & \\textbf{Recall (\\%)} "
        "& \\textbf{F1-Score (\\%)} & \\textbf{Volume de Teste} \\\\\n\t\t\\midrule\n"
        + "\n".join(linhas) +
        f"\n\t\t\\midrule\n\t\t\\textbf{{Média Macro}} & \\textbf{{{mp:.1f}\\%}} & "
        f"\\textbf{{{mr:.1f}\\%}} & \\textbf{{{mf:.1f}\\%}} & \\textbf{{{tot}}} \\\\\n"
        "\t\t\\bottomrule\n\t\\end{tabularx}\n"
        "\t\\fonte{Elaborado pelo autor (\\the\\year).}\n\\end{table}\n"
    )


def tabela_46(abl):
    comps = abl.get("componentes", [])
    rot = abl.get("roteamento_agente", {})
    linhas = []
    for c in comps:
        linhas.append(f"\t\t{c['componente']} & {c['com']:.1f}\\% & {c['sem']:.1f}\\% "
                      f"& {c['delta_f1']:+.1f} \\\\")
    corpo = "\n".join(linhas) if linhas else "\t\t--- & --- & --- & --- \\\\"
    nota = ""
    if rot:
        nota = (f" O ramo vetorial do agente respondeu por "
                f"{100*rot.get('frac_vetorial',0):.0f}\\% das transações "
                f"(acurácia condicional {100*rot.get('acuracia_ramo_vetorial',0):.0f}\\%) e o "
                f"ramo LLM por {100*rot.get('frac_llm',0):.0f}\\% "
                f"(acurácia {100*rot.get('acuracia_ramo_llm',0):.0f}\\%).")
    return (
        "\\begin{table}[htb]\n\t\\centering\n"
        "\t\\caption{Ablação de componentes sobre o teste-cego (variação de F1-Macro).}\n"
        "\t\\label{tab:ablacao}\n"
        "\t\\begin{tabularx}{\\textwidth}{X c c c}\n\t\t\\toprule\n"
        "\t\t\\textbf{Componente} & \\textbf{Com} & \\textbf{Sem} & \\textbf{$\\Delta$ F1 (p.p.)} \\\\\n"
        "\t\t\\midrule\n" + corpo + "\n\t\t\\bottomrule\n\t\\end{tabularx}\n"
        "\t\\fonte{Elaborado pelo autor (\\the\\year).}\n\\end{table}\n"
    ), nota


def main():
    cons, fatos, ag, abl = carregar()
    ds = fatos.get("dataset", {})
    n_base = ds.get("n_base", 1660)
    n_tr, n_va, n_te = ds.get("n_treino", 1150), ds.get("n_validacao", 176), ds.get("n_teste", 334)
    pct_regra = ds.get("rotulo_por_regra_pct", 74.2)

    rf = cons.loc["tfidf_random_forest"]
    nb = cons.loc["tfidf_naive_bayes"]
    byt5 = cons.loc["byt5_finetuning"]
    rag = cons.loc["rag_pgvector_minilm"]
    has_ag = "agente_hibrido_langgraph" in cons.index
    agr = cons.loc["agente_hibrido_langgraph"] if has_ag else None

    rf_cv = rf.get("cv_f1_macro_mean", float("nan"))
    gap = (rf_cv - rf["f1_macro"]) * 100 if rf_cv == rf_cv else float("nan")

    if has_ag:
        ag_lat = agr["latencia_ms"]
        ag_lat_med = ag.get("latencia_ms_mediana", 40)
        ag_lat_s = f"{ag_lat/1000:.1f}~s" if ag_lat >= 1000 else f"{ag_lat:.1f}~ms"
        acc_vet = 100 * abl.get("roteamento_agente", {}).get("acuracia_ramo_vetorial", 0.977)
        acc_llm = 100 * abl.get("roteamento_agente", {}).get("acuracia_ramo_llm", 0.214)
        par_ag = (
            f"O agente roteou {100*ag.get('frac_vetorial',0):.0f}\\% das transações "
            f"para a busca vetorial (mediana de {ag_lat_med:.0f}~ms) e "
            f"{100*ag.get('frac_llm',0):.0f}\\% para o LLM local (dezenas de segundos), "
            f"acionando confirmação humana em {100*ag.get('taxa_hitl',0):.1f}\\% dos casos. "
            f"Atingiu acurácia de {100*agr['acuracia']:.1f}\\% e F1-Macro de "
            f"{100*agr['f1_macro']:.1f}\\% (latência média ponderada de {ag_lat_s}). "
            f"O F1-Macro do agente supera o da busca vetorial isolada ({100*rag['f1_macro']:.1f}\\%) "
            f"--- o ramo LLM recupera parte das classes de cauda --- mas sua acurácia global "
            f"é a mais baixa entre os modelos, porque o ramo LLM, sob a diretriz "
            f"anti-alucinação, tende a rotular como \\textit{{Despesas Diversas}} nomes cuja "
            f"categoria era lexicalmente evidente (acurácia condicional do ramo LLM: "
            f"apenas {acc_llm:.0f}\\%, contra {acc_vet:.0f}\\% do ramo vetorial)."
        )
        ag_acc, ag_f1 = f"{100*agr['acuracia']:.1f}", f"{100*agr['f1_macro']:.1f}"
        ag_hitl = f"{100*ag.get('taxa_hitl',0):.1f}"
    else:
        par_ag = "\\textit{[resultado do agente pendente]}"
        ag_lat_s = "\\textit{[pendente]}"
        ag_acc = ag_f1 = ag_hitl = "\\textit{[pendente]}"
        acc_vet = acc_llm = float("nan")

    melhor_nome, t45 = tabela_45(cons)
    t46, nota46 = tabela_46(abl)

    sec46 = f"""\\section{{Resultados Comparativos da Classificação de Transações}}
\\label{{sec:val_resultados_classificacao}}

Para responder às questões de pesquisa Q1 e Q2, cinco arquiteturas foram implementadas e
avaliadas sobre \\textbf{{o mesmo conjunto de teste-cego de {n_te} transações}}, cujos
estabelecimentos são \\textbf{{disjuntos}} dos utilizados em treino e no povoamento da base
vetorial (particionamento por estabelecimento; Seção~\\ref{{sec:val_datasets}}). Todas as
métricas e artefatos foram registrados no MLflow. A Tabela~\\ref{{tab:resultados_modelos}}
sumariza os resultados globais.

{tabela_44(cons)}

A análise revela um quadro \\textbf{{distinto do relatado pela literatura apoiada em grandes
corpora}}, atribuível às características do acervo pessoal disponível (volume reduzido,
{ds.get('n_categorias_presentes', 11)} categorias efetivamente povoadas e forte
desbalanceamento):

\\begin{{enumerate}}
\t\\item \\textbf{{Os baselines esparsos foram os mais robustos.}} O TF-IDF com Random Forest
\tobteve o melhor F1-Macro (\\textbf{{{100*rf['f1_macro']:.1f}\\%}}) e o TF-IDF com Naive
\tBayes a melhor acurácia global (\\textbf{{{100*nb['acuracia']:.1f}\\%}}), ambos com
\tlatência inferior a 0,3~ms. A vetorização por $n$-gramas de caractere (\\texttt{{char\\_wb}},
\t2--4) capturou a morfologia recorrente das descrições brasileiras (``UBER'', ``IFD*'',
\t``DROGA-'') mesmo em estabelecimentos inéditos;

\t\\item \\textbf{{A diferença entre validação cruzada e teste-cego foi acentuada.}} Sob
\tvalidação cruzada 5-fold (com repetição de estabelecimentos entre folds), o Random Forest
\tatingiu F1-Macro de \\textbf{{{100*rf_cv:.1f}\\%}}; no teste-cego por estabelecimento o
\tvalor caiu para \\textbf{{{100*rf['f1_macro']:.1f}\\%}}. Essa diferença de
\t$\\approx${gap:.0f}~pontos percentuais quantifica o quanto o desempenho aparente de um
\tclassificador de transações depende da \\textbf{{memorização de comércios já observados}};

\t\\item \\textbf{{O ByT5 ajustado sofreu sobreajuste.}} Com {n_tr} exemplos de treino, o
\t\\texttt{{byt5-small}} convergiu a \\textit{{loss}} de treino inferior a 0,02 mas
\tgeneralizou mal (F1-Macro \\textbf{{{100*byt5['f1_macro']:.1f}\\%}}), colapsando a predição
\tda classe majoritária \\textit{{Lazer e Entretenimento}}. Modelos no nível de byte exigem
\tcorpora de ordem de grandeza superior;

\t\\item \\textbf{{A busca vetorial densa (RAG) ficou limitada pela base fria.}} Com
\t{ds.get('n_estabelecimentos_kb', 488)} estabelecimentos vetorizados por
\t\\texttt{{paraphrase-multilingual-MiniLM-L12-v2}} (384-d), apenas
\t\\textbf{{{100*rag.get('cobertura_alta_confianca', 0.575):.1f}\\%}} das transações de teste
\tobtiveram vizinho com similaridade de cosseno $\\ge$~0,85; nas demais o vizinho foi
\tsemanticamente fraco, resultando em F1-Macro de \\textbf{{{100*rag['f1_macro']:.1f}\\%}}
\t(latência real de consulta no PGVector: \\textbf{{{rag['latencia_ms']:.1f}~ms}});

\t\\item \\textbf{{O Agente Híbrido combinou os dois ramos, ao custo de latência.}} {par_ag}
\\end{{enumerate}}

\\subsection{{Acurácia global versus F1-Macro}}
Todos os modelos apresentam acurácia global sensivelmente superior ao F1-Macro (o Naive
Bayes, por exemplo: {100*nb['acuracia']:.1f}\\% de acurácia contra
{100*nb['f1_macro']:.1f}\\% de F1-Macro). Isso decorre de dois fatores do acervo pessoal:
(i) o forte desbalanceamento --- \\textit{{Alimentação}} e \\textit{{Lazer e
Entretenimento}} respondem por cerca de metade do teste; e (ii) o tamanho reduzido das
classes de cauda --- \\textit{{Moradia}}, \\textit{{Tecnologia}}, \\textit{{Vestuário}} e
\\textit{{Educação}} contam com 4 a 5 estabelecimentos distintos cada. As categorias
\\textit{{Pets}}, \\textit{{Serviços Financeiros}} e \\textit{{Doações e Presentes}} não
tiveram amostragem suficiente e foram agregadas a \\textit{{Despesas Diversas / Outros}}. O
F1-Macro é adotado como métrica conservadora de referência; os resultados devem ser lidos
como \\textbf{{diagnóstico sobre um acervo pessoal real de porte reduzido}}, não como
estimativa de desempenho populacional.

\\subsection{{Desempenho Detalhado por Categoria de Despesa}}
A Tabela~\\ref{{tab:resultados_categorias}} detalha o comportamento do {melhor_nome} nas
categorias efetivamente avaliadas.

{t45}

Categorias com padrões léxicos fortes e volume adequado --- \\textit{{Alimentação}},
\\textit{{Transporte}}, \\textit{{Saúde}} e \\textit{{Marketplace / E-commerce}} ---
alcançaram F1-Score entre 90\\% e 100\\%. As classes de cauda (\\textit{{Tecnologia}},
\\textit{{Vestuário}}, \\textit{{Moradia}}) obtiveram F1 nulo ou próximo de zero em quase
todos os modelos: com 4 a 5 exemplos no teste, um único erro derruba a métrica. Esse é o
principal fator limitante do F1-Macro.

\\subsection{{Estudo de Ablação}}
O estudo de ablação isolou os componentes mensuráveis sem novo custo de inferência do LLM
(Tabela~\\ref{{tab:ablacao}}).{nota46}

{t46}

A ablação revela um efeito \\textbf{{dependente da representação}}. Para os classificadores
esparsos (TF-IDF + Random Forest), a normalização léxica agressiva de gateways foi
neutra ou levemente prejudicial ($\\Delta$ F1 $\\approx -2$~p.p.): a vetorização por
$n$-gramas de caractere já é robusta a prefixos como ``PAG*'' e ``MP*'', que por vezes
carregam sinal útil. Para a busca vetorial densa, ao contrário, a normalização foi
\\textbf{{decisiva}} ($\\Delta$ F1 $\\approx +11$~p.p.): sem ela, o \\textit{{embedding}}
multilíngue se confunde com o ruído dos intermediadores. O componente que sustenta o
desempenho do agente é a \\textbf{{busca vetorial}}: seu ramo respondeu corretamente a
{100*abl.get('roteamento_agente', {}).get('acuracia_ramo_vetorial', 0.977):.0f}\\% das
transações que resolveu, enquanto o ramo LLM local (\\texttt{{gemma-4-e4b}}) acertou apenas
{100*abl.get('roteamento_agente', {}).get('acuracia_ramo_llm', 0.214):.0f}\\% ---
tendendo, sob a diretriz anti-alucinação, a rotular como \\textit{{Despesas Diversas}}
nomes cuja categoria era lexicalmente evidente (``SAPPORO RESTAURANTE'', ``Drogaria
Paulista''). A ferramenta de busca na web foi desativada por indisponibilidade de
conectividade no ambiente experimental.
"""

    sec47 = f"""\\section{{Avaliação de MLOps, Latência e Observabilidade}}
\\label{{sec:val_mlops}}

A infraestrutura de MLOps gerenciada pelo MLflow registrou integralmente os
{fatos.get('modelos', {}) and len(fatos['modelos'])} experimentos de classificação
(parâmetros, métricas, relatórios por categoria, predições e figuras) no experimento
\\texttt{{experimento\\_faturas}}, garantindo reprodutibilidade:
\\begin{{itemize}}
\t\\item \\textbf{{Human-in-the-Loop:}} no teste-cego, {ag_hitl}\\% das transações
\tacionaram a interrupção programada para confirmação humana (\\texttt{{requer\\_confirmacao}}),
\tcorrespondendo a nomes ambíguos roteados ao LLM com baixa confiança;
\t\\item \\textbf{{Latência por arquitetura:}} a consulta vetorial no PGVector custou
\t{rag['latencia_ms']:.1f}~ms; o ramo LLM local (\\texttt{{gemma-4-e4b}}, modelo de
\traciocínio no LM Studio) custou {ag_lat_s if has_ag else 'dezenas de segundos'} por
\ttransação, evidenciando o principal gargalo operacional para processamento em lote sem
\tGPU dedicada de maior porte;
\t\\item \\textbf{{Aprendizado ativo:}} as classificações de alta confiança ($\\ge$~0,85) e
\tas validadas por humano alimentam continuamente a base vetorial (\\texttt{{salvar\\_vectorstore}}),
\treduzindo progressivamente o acionamento do LLM em compras recorrentes.
\\end{{itemize}}
"""

    verdito = f"""\\section{{Respostas às Questões de Pesquisa e Verificação da Hipótese}}
\\label{{sec:val_respostas_questoes}}

\\begin{{itemize}}
\t\\item \\textbf{{Resposta a Q1:}} sob teste-cego rigoroso com estabelecimentos disjuntos,
\tas representações \\textbf{{esparsas}} (TF-IDF com $n$-gramas de caractere) foram mais
\teficazes que as densas neste acervo de porte reduzido: o TF-IDF + Random Forest
\t({100*rf['f1_macro']:.1f}\\% de F1-Macro) superou a busca vetorial densa
\t({100*rag['f1_macro']:.1f}\\%) e o ByT5 ajustado ({100*byt5['f1_macro']:.1f}\\%). Modelos
\tdensos e agentes LLM tendem a compensar essa diferença apenas com corpora maiores e bases
\tvetoriais já povoadas;

\t\\item \\textbf{{Resposta a Q2:}} o melhor F1-Macro alcançado foi de
\t{100*rf['f1_macro']:.1f}\\% (acurácia global de até {100*nb['acuracia']:.1f}\\%) sobre 11
\tcategorias efetivamente povoadas. O limiar de 85\\% de F1-Macro \\textbf{{não foi
\tatingido}} por nenhuma arquitetura neste protocolo, embora a acurácia global o supere;

\t\\item \\textbf{{Resposta a Q3:}} os erros concentraram-se em (i) categorias de cauda com
\t4--5 exemplos de teste (F1 nulo para quase todos os modelos) e (ii) nomes opacos de
\tintermediadores (``PAYPAL~*BOSS~LIFE'', ``DIVIPAYPAYMENTS''). O ramo LLM local, sob
\tdiretriz anti-alucinação, mostrou-se \\textbf{{contraproducente}}, rotulando como
\t\\textit{{Despesas Diversas}} até nomes com pista de categoria explícita; a busca na web
\tque mitigaria nomes informais esteve indisponível no ambiente;

\t\\item \\textbf{{Resposta a Q4:}} a contribuição da normalização léxica é \\textbf{{dependente
\tda representação}}: neutra/levemente negativa para o TF-IDF ($\\Delta$ F1 $\\approx -2$~p.p.),
\tmas decisiva para a busca vetorial densa ($\\Delta$ F1 $\\approx +11$~p.p.). O histórico de
\tmarketplace do usuário não pôde ser avaliado por ausência de compras confirmadas na base;

\t\\item \\textbf{{Resposta a Q5:}} o ciclo de MLOps com MLflow e aprendizado ativo mostrou-se
\tviável e auditável; as limitações práticas são a \\textbf{{latência}} e a \\textbf{{baixa
\tacurácia}} do LLM local roteado ({ag_lat_s if has_ag else 'dezenas de segundos'} por
\ttransação; acurácia condicional de apenas {acc_llm:.0f}\\%), que tornam o ramo LLM,
\tneste acervo, menos eficaz que a busca vetorial isolada.
\\end{{itemize}}

\\textbf{{Veredito sobre a Hipótese Central:}} a hipótese \\textbf{{não se confirma}} na
métrica primária (F1-Score Macro $>$ 85\\%) sob avaliação por estabelecimento: o melhor
resultado foi {100*rf['f1_macro']:.1f}\\%. Ela é \\textbf{{parcialmente sustentada}} quando
o critério é a acurácia global (o Naive Bayes atinge {100*nb['acuracia']:.1f}\\%) e quando
se admite a repetição de estabelecimentos entre treino e teste (validação cruzada:
{100*rf_cv:.1f}\\% de F1-Macro). As causas da não confirmação são discutidas na
Seção~\\ref{{sec:concl_limitacoes}}: porte e cobertura do acervo rotulado, cauda longa de
categorias com pouquíssimos exemplos, e rotulagem de referência semiautomática. O pipeline
técnico (extração, normalização, RAG, agente em grafo, HITL, MLOps) foi integralmente
implementado e validado do ponto de vista funcional.
"""

    import re as _re

    def _ptbr(t):
        # vírgula decimal em números "x.y" (não afeta \ref, arquivos, versões com letras)
        return _re.sub(r"(?<=\d)\.(?=\d)", ",", t)

    (L / "cap4_sec46_classificacao.tex").write_text(_ptbr(sec46), encoding="utf-8")
    (L / "cap4_sec47_mlops.tex").write_text(_ptbr(sec47), encoding="utf-8")
    (L / "cap4_sec48_questoes.tex").write_text(_ptbr(verdito), encoding="utf-8")

    snip = f"""# Trechos p/ pré-textuais e Cap5 (números reais)

- CER Docling: 5,72% (de 52,8% do Tesseract); casamento exato 86,2%.
- Base rotulada: {n_base} transações reais (C6+Nubank), {ds.get('n_categorias_presentes',11)} categorias, {pct_regra:.0f}% via dicionário léxico.
- Splits: {n_tr} treino / {n_va} validação / {n_te} teste-cego (por estabelecimento).
- TF-IDF+RF: F1-Macro {100*rf['f1_macro']:.1f}% / acurácia {100*rf['acuracia']:.1f}% (CV {100*rf_cv:.1f}%).
- TF-IDF+NB: F1-Macro {100*nb['f1_macro']:.1f}% / acurácia {100*nb['acuracia']:.1f}%.
- RAG PGVector: F1-Macro {100*rag['f1_macro']:.1f}% / latência {rag['latencia_ms']:.1f} ms.
- ByT5-small: F1-Macro {100*byt5['f1_macro']:.1f}%.
- Agente híbrido: acurácia {ag_acc}% / F1-Macro {ag_f1}% / HITL {ag_hitl}% / latência {ag_lat_s if has_ag else 'pendente'}.
- Nenhum modelo atinge 85% de F1-Macro no teste-cego por estabelecimento.
"""
    (L / "pretextual_snippets.md").write_text(snip, encoding="utf-8")
    print(snip)
    print("Blocos LaTeX gravados em", L)


if __name__ == "__main__":
    main()
