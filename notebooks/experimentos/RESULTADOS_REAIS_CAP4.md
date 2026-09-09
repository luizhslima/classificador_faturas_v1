# Resultados reais — Capítulo 4 (classificação)

Pipeline reprodutível: `notebooks/experimentos/` (`common.py` + `01`–`08`).
Rastreamento: MLflow `http://192.168.15.18:5000` — experimento `experimento_faturas`.

## Base rotulada
- **1.660 transações reais** de faturas C6 Bank + Nubank (74% rotuladas por dicionário léxico
  de alta precisão; 26% pela categoria nativa do emissor mapeada).
- **11 categorias** efetivamente povoadas (Pets, Serviços Financeiros e Doações sem amostra
  suficiente → agregadas a *Despesas Diversas*).
- Split **por estabelecimento** (sem vazamento de merchant): 1.150 treino / 176 validação /
  **334 teste-cego**.

## Tabela 4.4 — Comparativo global (teste-cego de 334, estabelecimentos disjuntos)

| Modelo | Acurácia | Precisão-M | Recall-M | F1-Macro | Latência | CV 5-fold F1 |
|---|---|---|---|---|---|---|
| TF-IDF + Naive Bayes | **88,3%** | 69,8% | 61,7% | 63,6% | 0,03 ms | 88,5% |
| **TF-IDF + Random Forest** | 84,7% | 74,2% | 66,5% | **69,3%** | 0,28 ms | 92,7% |
| ByT5 fine-tuning (byt5-small) | 65,9% | 52,0% | 53,0% | 48,3% | 65 ms | — |
| RAG PGVector (MiniLM 384-d) | 82,6% | 57,9% | 55,4% | 56,2% | 1,4 ms | — |
| Agente Híbrido (LangGraph + gemma-4-e4b) | 61,4% | 68,4% | 62,9% | 60,0% | 6,5 s | — |

## Achados

1. **Baselines esparsos vencem** neste acervo pequeno e ruidoso. TF-IDF + n-gramas de
   caractere generaliza melhor que embeddings densos e que o ByT5 (sobreajuste com 1.150
   exemplos).
2. **Nenhum modelo atinge 85% de F1-Macro** no teste-cego por estabelecimento → hipótese
   central **não confirmada na métrica primária**; parcialmente sustentada em acurácia
   global (NB: 88,3%).
3. **Gap CV × teste-cego ≈ 23 p.p.** (RF: 92,7% → 69,3%) = efeito de memorização de
   comércios já vistos.
4. **Agente:** ramo vetorial resolve 52% das transações com **acurácia condicional de 98%**;
   ramo LLM local (gemma-4-e4b) responde por 48% com **apenas 21%** de acurácia — sob a
   diretriz anti-alucinação tende a rotular como *Despesas Diversas* nomes com pista de
   categoria evidente. HITL: 4,5%. Busca web (DuckDuckGo) **indisponível no ambiente**.
5. **Ablação da normalização léxica:** decisiva para o RAG denso (**+11 p.p.** de F1) mas
   neutra/levemente negativa para o TF-IDF (−2 p.p.).
6. **Cauda longa:** Tecnologia, Vestuário, Moradia (4–5 comércios no teste) → F1 nulo em
   quase todos os modelos; principal fator que derruba o F1-Macro.

## OCR (já era real — mantido)
Docling V2 vs Tesseract: CER 5,72% × 52,8%; casamento exato 86,2% × 3,3%; 1.398 transações
auditadas. (O "1,12%" do Resumo/Abstract/Cap5 era erro de digitação — corrigido para 5,72%.)

## Gravação no Postgres
- `estabelecimentos` + coleção PGVector `baseconhecimento`: **488 estabelecimentos** do
  treino, vetorizados.
- `transacoes`: predições do agente gravadas em amostra pseudoaleatória de **800**
  transações Nubank (`--gravar --limite 800`), com `categoria_id`, `confianca`,
  `metodo_classificacao`, `status_classificacao` (`classificada` / `sugerida` p/ baixa
  confiança). Job longo em execução.

## Arquivos gerados
- `resultados/consolidado_modelos.csv`, `resultados/por_categoria__*.csv`,
  `resultados/predicoes__*.csv`, `resultados/ablacao.{csv,json}`,
  `resultados/agente_metricas.json`, `resultados/fatos_cap4.json`
- `resultados/latex/` — blocos LaTeX prontos (aplicados ao Cap. 4)
- `resultados/*.png` e `docs/TCC - Final/assets/grafico_*.png` — figuras 7–9
