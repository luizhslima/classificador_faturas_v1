# Aplicação da verificação final de 22/09/2026 (`Verificacao_final_2026-09-22.md`)

Aplicado em 22/09/2026. Compilação limpa (pdflatex → bibtex → pdflatex ×2, com o autobuild do editor encerrado): **163 páginas**, 0 erros, 0 referências ou citações indefinidas, rótulos estáveis, bibtex sem avisos, 74 referências. A maior sobra de margem caiu de 18,7 pt para 10,4 pt (*prompt* literal do Apêndice D, reproduzido sem edição).

## Crítico

| Item | Ação |
|---|---|
| K-1: Quadro 5 × dados | Quadro refeito com 6 linhas copiadas de `data/c6_ocr_benchmark_transactions.csv`. A distância é calculada sobre a transação completa, e cada linha tem uma coluna "Fenômeno observado": valor desvinculado, fusão de colunas, asterisco lido como aspas, 0 lido como O, lançamento não recuperado e erro residual do Docling. Passou a `tabularx` em `\scriptsize`, porque o `\resizebox` deixava o quadro ilegível. No Quadro 1, "UBER\* TRIP VALORES EM REAIS" foi trocado pelo caso real `IFD"PUNTO ITAQUA COMER`. A §5.5.3, item 1, agora trata "JUROS DE MORA" como pareamento de lançamento não recuperado (100 das 699 transações; 47,5% não recuperados). O item 2 declara o erro residual do Docling: 86 lançamentos, 49 deles em 2022-04 e 2023-02, e 34 com descrição correta e valor de outra linha. Os números foram conferidos no arquivo. |

## Moderados

| Item | Ação |
|---|---|
| M-1: "por estabelecimento" | 7 pontos corrigidos para "por descrição normalizada": §5.3.3 (2), §5.6, §5.6.2, §5.8, §5.9 e §6.2. Na §5.6.2, a frase sobre o Cinépolis passou a dizer que não há nenhuma ocorrência no treino, nem sob outra grafia (conferido em `split_treino.csv`). |
| M-2: TAB em `\textit` | `(\textit{5-fold cross-validation})` |
| M-3: "quantifica" | "é compatível com um efeito de memorização…, do qual constitui um limite inferior" |
| M-4: nota da Tabela 5 | "até 1,5 p.p., sem alterar a ordem nem a magnitude da vantagem", com os números por transação (EMR 87,7/2,9; CER 4,97/52,43) |
| M-5: `data/` não versionado | A nota da Tabela 5 e o Apêndice C declaram que os CSV ficam fora da distribuição pública, porque o arquivo de transações contém as transações reais auditadas. A §6.2, item 8, registra que o *script* da bateria de extração não está depositado. |
| M-6: etapas 01–13 | §4.9 e Apêndice C, com a descrição das etapas 12 e 13. O Apêndice C informa que as etapas 11–13 foram acrescentadas depois dos experimentos, sem reexecutar modelos. |
| M-7: margens | Cabeçalho da Tabela 2 encurtado; larguras da Tabela 1 ajustadas. Ambas sem transbordo. |

## Leves (todos aplicados)

1. **Ficha catalográfica:** palavras-chave alinhadas ao Resumo.
2. **Cabeçalho do autor:** `\autorabr` → "LIMA, L. H. M. S. de".
3. **`.bib`:**
   - Santos → `@thesis`, que produz "Trabalho de Conclusão de Curso (Graduação em Engenharia de Computação)";
   - Chapman → `@book`, com "Chicago: SPSS";
   - Luhn → "Washington, DC: United States Patent Office".
4. **Contagem da base vetorial:** "488 chaves (descrições normalizadas)" na §5.6, item 4, e no Apêndice B.2. Na §4.7, item 4, "(a descrição já tem correspondente próximo na base vetorial)".
5. **§5.6.5:** "o mesmo fenômeno da sobreposição de 44%".
6. **§4.3:** "faturas reais, com as transações pseudonimizadas na base".
7. **Anexo A:** "princípio da necessidade (… não são extraídos dos documentos)".
8. **Objetivo geral e §6.2:** "conceber e implementar … de ponta a ponta … e avaliar experimentalmente seus componentes". Na síntese final, "com resultados de classificação reprodutíveis a partir do repositório".
9. **Vieses de redação removidos:** "rigorosa/rigoroso/rigorosas", "moderna", "estrita conformidade" e "com folga".
10. **Rótulos em caixa baixa:**
    - §3.4/§3.6: "Validação e resultados", "Relação com esta pesquisa";
    - §4.9: os três rótulos;
    - §5.3: os três rótulos;
    - §4.7, itens 2 e 6.
11. **Estrangeirismos:**
    - *strings* → expressões (Apêndice A);
    - *thread* → linha de execução;
    - *slots* → posições de atendimento;
    - *backend* → mecanismo de busca;
    - *fallback* → descrição por extenso;
    - *run* → execução;
    - *string* → cadeia.
12. **Maiúsculas no meio da frase:** *data drift* e *concept drift* (Q5 na §4.2 e na §5.8), "aprendizado ativo (*active learning*)" (§2.5.2 e Q5) e "As florestas aleatórias". Também "sistema operacional" (§5.2).
13. **Siglas:**
    - acrescentadas IA e IC, definidas na primeira ocorrência (Cap. 1 e §5.4.3);
    - removidas BI, ORM, RNN, ICLR e SBBD (sem uso no corpo).
    - A lista passa a 82 entradas.
14. **"Faturas" → "transações de faturas":** §2.6, §4.1 e Recomendação prática (§6.3).
15. **Outros:**
    - "Minicomputador";
    - servidor de infraestrutura rotulado como "camadas de dados conteinerizadas";
    - §2.6 remete só ao Capítulo 5;
    - §5.9 "desde a extração de documentos";
    - Apêndice C inclui a Figura 5 e o Quadro 5 entre os derivados dos CSV;
    - CPGF caracterizado por `notebooks/data_analysis.ipynb`.
16. **Bloco 5 de limitações:** novo item 7 no bloco de consolidação da §6.5 (expressão de busca complementar na ACM e na SBC OpenLib e caracterização de desvio sobre o acervo temporal). O item equivalente saiu do bloco de expansão.

## Varredura pós-aplicação

- Zero ocorrências de "extit", "meio ponto", "VALORES EM REAIS", "IFOOD IFD MR", "quantifica o efeito", "etapas 01 a 11", "distribui os artefatos", "rigoros", "com folga", "Data Drift", "Active Learning", "strings", "Geração aumentada por recuperação", "minimização de dados" e "Validação e Resultados".
- As 6 ocorrências restantes de "por estabelecimento" são legítimas: limite de 12 por estabelecimento, "partição estrita por estabelecimento" e "nem por estabelecimento".

## Pendências do autor (inalteradas)

1. Data e assinatura do Anexo A.
2. Release/etiqueta, rotação de credenciais, publicação do submódulo `web`, Zenodo (opcional).
3. Depósito do *script* da bateria de extração.
4. Correção do registro `epochs`/`lr` do ByT5 no MLflow.
5. Turnitin antes do depósito.
6. Desligar o autobuild do editor (LaTeX Workshop) durante compilações externas: ele corrompe os `.aux` e travou um arquivo nesta rodada.
