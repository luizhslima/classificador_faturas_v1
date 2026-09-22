# Verificação final da monografia contra os critérios de todos os relatórios (22/09/2026)

**Versão verificada:** `docs/TCC - Final/USPSC-modelo-ICMC-PORTUGUES.pdf`, 161 páginas, compilado em 22/09/2026 15:11 (commit `cda7688`, branch `revisao-2026-09-21`).

**Critérios aplicados:** os mesmos dos seis relatórios anteriores:

1. Relatório do Prof. Ciferri (08/07/2026): estrutura, rascunhos, ABNT 1:1, pessoa do discurso, ortografia, remissões;
2. Revisão de 17/09 (E, I, T, R, S, V, N, A, W, G; 103 achados);
3. Validação contra as aulas do MBA (18/09; C1–C3, M1–M8, L1–L8);
4. Cruzamento texto × código (19/09);
5. Revisão de 19/09 (96 achados);
6. Revisão de 21/09 (C-01/C-02, M-01–M-17, L-01–L-22) e as três verificações posteriores registradas em `Aplicacao_revisao_2026-09-21.md`.

**Método:**

- Leitura integral do texto extraído do PDF.
- Varredura automática de 45 padrões (termos corrigidos, números antigos, grafias e estrangeirismos).
- Cruzamento citações × referências, siglas × uso, rótulos × remissões.
- Busca de caracteres de controle no fonte.
- Conferência dos números da bateria de extração contra `data/c6_ocr_benchmark_*.csv`.
- Verificação de existência e versionamento dos arquivos que o texto cita.

---

## 1. O que está resolvido (confirmado)

- **Compilação:** 0 referências/citações indefinidas, `bibtex` sem avisos; **74 chaves citadas = 74 entradas na lista** (1:1). `nbr14724` só aparece em arquivos do modelo não incluídos.
- **Rascunhos, primeira pessoa e antecipação:** nenhuma marca de rascunho, nenhuma primeira pessoa fora de dedicatória e agradecimentos, e nenhuma antecipação de resultado na Introdução (MBA C3).
- **Termos corrigidos:** nenhuma ocorrência de "teste-cego", "subhipótese", "SOTA", "Table Transformer", "RSL-n", "Meta TCC", "Agente Hibrido", "PGVector", "5,72", "52,82", "9,2×", "estabelecimentos disjuntos" ou "sem sobreposição de comércios".
- **Números conferidos:** Tabela 5 confere com os dados (5,69/52,86; 9,3×; 8,4×; 8,5×; 9,1×; +9,4; +82,9 p.p.; 1,6×). Também conferem 1.150 + 176 + 334 = 1.660, a Tabela 18 (30 correspondências), a Tabela 17 (30 grupos) e a Tabela 2 (49 faturas, 357 páginas).
- **Resumo e abstract:** 415 e 379 palavras (faixa de 150–500). Palavras-chave iguais no resumo, no abstract e nos metadados do PDF.
- **Veredito qualificado (C-01):** "para a configuração avaliada" aparece no Resumo/Abstract, em 5.2.1, 5.8, 5.9, 6.2 e 6.3.
- **Extração × classificação (C-02):** a conclusão 1 está restrita à qualidade da transcrição.
- **Figura 2 × Quadro 4:** coerentes. Fonte → Nota nas Figuras 1 e 2.
- **Apêndices:** os seis declarados na Introdução correspondem aos existentes.

---

## 2. Pendências encontradas

### CRÍTICO

**K-1: o Quadro 5 não corresponde ao arquivo de dados da bateria de extração.** Esse problema também alcança o bloco inferior do Quadro 1 e a §5.5.3.

- **Onde:** `USPSC-Cap4-Avaliacao_Experimental.tex:305-311`, `USPSC-Cap1-Introducao.tex:25`, `USPSC-Cap4-Avaliacao_Experimental.tex:291`.
- **Critério:** números e amostras apresentados como reais devem bater com os dados. É o mesmo critério da "Figura 1 fabricada" (parecer do Prof. Ciferri) e do M-01 de 21/09.
- **O que os dados mostram:** o arquivo é `data/c6_ocr_benchmark_transactions.csv`, a mesma fonte das Tabelas 5 e 6.

| Linha do Quadro 5 | O quadro diz | O arquivo diz |
|---|---|---|
| ASSAI 370,33 | Tesseract "ASSAI ATACADISTA 370,33", Lev 0 | saída "ASSAI ATACADISTA" (sem valor), Lev da transação 7 |
| DL HELPHBOMAXCOM 13,95 | "…13,95", Lev 0 | sem valor, Lev 6 |
| CLUBE DO INGRESSO 106,94 | "…PARCELA 1/2 106,94", Lev 14 | sem valor; Lev 14 é o da descrição, e o da transação é 13 |
| EBANX SPOTIFY 34,90 | "JUROS DE MORA 34,90", Lev 12 | "JUROS DE MORA **0,00**", Lev da transação 15 (12 é o da descrição) |
| 2024-01 UBER TRIP 19,99 | referência "UBER TRIP"; Tesseract "UBER* TRIP VALORES EM REAIS 19,99", Lev 18 | referência "UBER\* TRIP"; Tesseract pareado com **"R$ 5.867,51"**, Lev 13. A string "VALORES EM REAIS" não existe em nenhum artefato do repositório (CSV, notebooks, scripts) |
| 2025-08 IFOOD \*IFD\*MR DELIVE 51,97 | Tesseract "IFOOD IFD MR DELIVE 51,97", Lev 3 | a transação é de **2024-01**, e o Tesseract produziu "IFOOD \*IFD\*MR DELIVE" (descrição exata), Lev 6 |

- **Diagnóstico:** as distâncias do quadro são da descrição isolada, mas as células mostram descrição + valor, com o valor da referência acrescentado às saídas do Tesseract.
- **Efeito sobre a §5.5.3:** o item 1 diz que o Tesseract "transcreveu erroneamente 'JUROS DE MORA' no lugar de 'EBANX SPOTIFY'". A §5.5.1 mostra que isso é artefato de pareamento: "JUROS DE MORA" é o trecho pareado em **100 das 699** transações do Tesseract.
- **Efeito sobre o Quadro 1:** o bloco inferior usa "UBER\* TRIP VALORES EM REAIS" como exemplo de ruído de OCR, sem respaldo nos dados.
- **Correção:** regenerar o Quadro 5 a partir de `c6_ocr_benchmark_transactions.csv`, com células e distância no mesmo nível (descrição, ou transação completa). Escolher exemplos reais de fusão de colunas (o CLUBE DO INGRESSO é real). Reescrever o item 1 da §5.5.3 como caso de lançamento não recuperado. Trocar o exemplo do Quadro 1 por um que conste do arquivo.

### MODERADO

**M-1: o critério de partição ainda aparece como "por estabelecimento" em 7 pontos.**

- **Critério:** 3ª verificação de 21/09. A própria §5.3.3 diz que "o restante do texto refere-se a 'teste cego por descrição' … e não a um teste por estabelecimento".
- **Onde:**
  - `Cap4:121`: "resultante do particionamento **aleatório** por estabelecimento" e "combinado ao particionamento por estabelecimento". "Aleatório" contradiz o próprio protocolo.
  - `Cap4:411` (§5.6, item 2): "no teste cego por estabelecimento".
  - `Cap4:493` (§5.6.2): "consequência do particionamento por estabelecimento".
  - `Cap4:709` (veredito da §5.8): "sob o protocolo de teste cego por estabelecimento".
  - `Cap4:752` (§5.9): "sob avaliação por estabelecimento".
  - `Cap5:22` (§6.2, item 7): "teste cego por estabelecimento".
- **Correção:** "por descrição normalizada". No `Cap4:121`, remover "aleatório".

**M-2: artefato LaTeX visível na §5.4.2.**

- **Onde:** `Cap4:133`.
- **Critério:** R01 (textos corrompidos) e M-12 (qualidade de composição).
- **O que aparece:** o PDF imprime "( extit5 partições cross-validation)". Um caractere TAB substituiu o `\t` de `\textit`, e o conteúdo é uma tradução automática espúria de "5-fold".
- **Correção:** remover o parêntese, porque "validação cruzada em 5 partições" já está no texto, ou escrever `(\textit{5-fold cross-validation})`.

**M-3: "quantifica o efeito de memorização" na §5.4.2.**

- **Onde:** `Cap4:133`, última frase.
- **Critério:** M-15(d) de 21/09, que pede "é compatível com", e o limite inferior da §5.3.3.
- **Correção:** "…é compatível com um efeito de memorização de comércios, do qual é um limite inferior (Seção 5.3.3)".

**M-4: a nota da Tabela 5 contradiz os dados.**

- **Onde:** `Cap4:207`.
- **Critério:** texto × tabela × dados (M-01 de 21/09).
- **O que está escrito:** "desloca os valores em menos de meio ponto percentual (por exemplo, casamento exato de 87,7% e 2,9% em vez de 86,2% e 3,3%)". O próprio exemplo desloca 1,5 p.p.
- **Pelo arquivo:** EMR do Docling 86,2 → 87,7 (+1,5), CER 5,69 → 4,97 (−0,7), WER 10,14 → 8,98 (−1,2).
- **Correção:** "desloca os valores em até 1,5 p.p., sem alterar a ordem nem a magnitude da vantagem".

**M-5: arquivos declarados como distribuídos não estão no repositório.**

- **Onde:** `Apendices:217` (Apêndice C) e `Cap4:207` (nota da Tabela 5).
- **Critério:** M-10 de 21/09 (reprodutibilidade) e Cruzamento 1.19.
- **O que está escrito:** "o repositório distribui os artefatos consolidados dessa bateria (`data/c6_ocr_benchmark_*.csv`)" e "valores reprodutíveis a partir de…".
- **Situação real:** o `.gitignore` exclui `data/`, e `git ls-files data` está vazio.
- **Correção de texto:** declarar que os arquivos ficam fora da distribuição por conterem as transações reais. Alternativa: versionar só o `summary.csv`, que tem apenas métricas por fatura e nenhuma descrição.

**M-6: a esteira citada como "etapas 01 a 11" já vai até a 13.**

- **Onde:** `Cap3:300` (§4.9) e Apêndice C (lista de `notebooks/experimentos/`).
- **Critério:** texto × código.
- **Situação:** a §5.4.3, a §5.5 e a §5.6 citam `13_classificacao_pos_extracao.py`, que calcula a concordância pós-extração e os McNemar do agente. A etapa `12_figuras.py` gera as Figuras 3–9. O Apêndice C não descreve 12 nem 13.
- **Mesma lacuna em outro ponto:** o Apêndice C diz que, após os experimentos, "o código recebeu **apenas** as correções editoriais do prompt". As etapas 11–13 foram acrescentadas depois, sem reexecutar modelos.

**M-7: a Tabela 2 invade a margem direita em 18,7 pt (≈ 6,6 mm).**

- **Onde:** `Cap4:59-72`.
- **Critério:** M-12 de 21/09 (margem de 2 cm).
- **Correção:** abreviar o cabeçalho "CSVs (verdade de referência)" ou usar `\resizebox`. As demais sobras são pequenas: Tabela 1, cabeçalho "Linguagem", 10,5 pt; *prompt* do Apêndice D, 10,4 pt.

### LEVE

1. **Ficha catalográfica com palavras-chave antigas.**
   - **Onde:** `USPSC-fichacatalografica.tex:47`.
   - **Critério:** E8 de 17/09 e M-17 de 21/09 (mesmo conjunto em todos os locais).
   - **O que está:** "Geração aumentada por recuperação. Reconhecimento óptico de caracteres".
   - **O que deveria estar, como no Resumo:** "Busca vetorial por similaridade. Extração de documentos com preservação de leiaute".
2. **Partícula do sobrenome no cabeçalho do resumo e do abstract.**
   - **Critério:** A5 de 17/09 (partícula por extenso).
   - **Situação:** a ficha grafa "Lima, Luiz Henrique Monteiro Silva **de**", e o cabeçalho do resumo "LIMA, L. H. M. S.".
   - **Pelo mesmo critério aplicado a SANTOS "dos" e SOUZA "de":** "LIMA, L. H. M. S. de". Ajustar `\autorabr`, se o orientador concordar.
3. **Referências ABNT (resíduos do L-14).**
   - **SANTOS (2022):** ainda sai "Monografia (Trabalho de Conclusão de Curso (Graduação…))", com parênteses aninhados. O campo `type` do `@monography` é embutido em "Monografia (…)"; usar `type = {Graduação em Engenharia de Computação}` ou equivalente.
   - **CHAPMAN et al. (2000):** sai "Chicago, 2000", sem a editora. O estilo não imprime `institution` de `@techreport`; acrescentar `publisher = {SPSS}`.
   - **LUHN (1960):** sai "Washington, DC: [S.l.: s.n.]", o mesmo defeito corrigido em Lewis e Gale. Acrescentar `publisher` (United States Patent Office).
4. **Contagem da base vetorial chamada de "estabelecimentos".**
   - **Onde:** `Cap4:423` ("488 estabelecimentos vetorizados") e `Apendices:149` ("um documento por estabelecimento único…, 488 estabelecimentos").
   - **Critério:** coerência com a correção da partição, pela qual são 488 **chaves (descrições normalizadas)**, como na Tabela 4.
5. **"Exatamente a sobreposição de 44%".**
   - **Onde:** `Cap4:610` (§5.6.5).
   - **Problema:** os 52% roteados ao ramo vetorial e os 44% de sobreposição são grandezas distintas.
   - **Correção:** "o mesmo fenômeno da sobreposição de 44%".
6. **"Faturas reais pseudonimizadas".**
   - **Onde:** `Cap3:40` (§4.3, etapa 2).
   - **Critério:** MBA M3 e §4.8.
   - **Problema:** as tabelas transacionais são pseudonimizadas, mas os PDFs da camada Bronze preservam nome e final do cartão por desígnio.
   - **Correção:** "transações reais pseudonimizadas".
7. **Anexo A, "minimização de dados sensíveis (… expurgados na ingestão)".**
   - **Onde:** `DeclaracaoIA:114`.
   - **Critério:** M-16 e MBA M3.
   - **Problema:** a §4.8 usa "princípio da necessidade", e "dados sensíveis" tem sentido legal próprio (art. 5º, II), que a §4.8 diz não se aplicar. Além disso, a §4.8 diz "não são extraídos", e não "expurgados".
   - **Correção:** "necessidade: números completos de cartão, CVV e senhas não são extraídos…".
8. **"Solução de ponta a ponta … avaliou experimentalmente".**
   - **Onde:** `Cap1:47` (objetivo geral) e `Cap5:14` (§6.2).
   - **Critério:** C-02, porque a avaliação não foi de ponta a ponta.
   - **Correção:** na §6.2, "concebeu e implementou uma solução de ponta a ponta e avaliou experimentalmente seus componentes".
   - **Mesma lógica:** "esteira completa, reprodutível" (`Cap5:47`) convive com o script da bateria de extração não depositado. Sugere-se "reprodutível na parte de classificação".
9. **Vieses de redação.**
   - **Critério:** revisão de 18/09 e L-20, que removeram "rigoroso", "moderno", "estrita" e "com folga".
   - **Onde restam:**
     - "análise rigorosa" (`CAPX:7`);
     - "protocolo rigoroso" (`Cap5:21`);
     - "condições rigorosas" (§5.8);
     - "suporte a dados moderna" (`Cap2:194`);
     - "estrita conformidade" (`Cap1:38`);
     - "o atende com folga" (`Cap4:704`).
10. **Rótulos em caixa de título.**
    - **Critério:** L-01 de 21/09.
    - **Onde:**
      - §3.4 e as nove subseções da §3.6: "Validação e Resultados", "Relação com esta Pesquisa";
      - §4.9: "Testes de Regressão de Modelo", "Validação de Integração Assistida", "Testes Unitários";
      - §5.3: "Conjunto de Dados Governamental…", "Acervo Real de Faturas…", "Ruído Real de…";
      - §4.7, itens 2 e 6: "Roteamento Pós-Normalização", "Roteador Unificado".
11. **Estrangeirismos que o L-16 mandou traduzir.**
    - "strings" (`Apendices:21` e `:49`);
    - "thread" (`Cap3:240`);
    - "slots paralelos" (§5.2);
    - "backend estável" e "fallback" (§6.5, itens 2 e 5);
    - "desse run" (nota da Tabela 4);
    - "string" (§5.5.3, item 1).
12. **Maiúsculas em estrangeirismos no corpo.**
    - **Critério:** L de 19/09, que ajustou só os títulos.
    - **Onde:** "Data Drift e Concept Drift" (`Cap3:18`, §4.2 Q5, e `Cap4:705`, §5.8 Q5); "Aprendizado Ativo (Active Learning)" (`Cap2:191`); "Florestas Aleatórias lidam…" no meio da frase (`Cap2:64`).
13. **Siglas.**
    - **Critério:** W10 de 17/09 e L-21 de 21/09.
    - **Usadas no corpo e ausentes da lista:** **IA** ("agentes de IA", legenda da Figura 1, §2.4.3, §2.5, §4.8) e **IC** ("IC 95%", em cinco pontos do Cap. 5 e do Cap. 6).
    - **Na lista e sem uso no corpo:** **BI**, **ORM** e **RNN** (o texto escreve por extenso); **ICLR** e **SBBD** (só nas referências). É o mesmo critério pelo qual BPE, CGU, VC e CNN foram removidas em 21/09.
14. **Objeto do trabalho descrito como "faturas".**
    - **Critério:** E7 de 17/09 (o objeto são as transações, não as faturas).
    - **Onde:** "classificar faturas de cartão" (`Cap2:201`), "extração e classificação de faturas" (`Cap3:6`) e "Para quem precise categorizar faturas" (Recomendação prática, §6.3).
15. **Outros ajustes pontuais.**
    - "Mini computador" → "minicomputador" (`Cap4:16`).
    - "Servidor de infraestrutura de dados (*data lakehouse* conteinerizado)" contraria a ressalva da §4.5 ("inspirada no paradigma").
    - A §2.6 diz "apurada empiricamente nos Capítulos 5 e 6"; a apuração é só no Capítulo 5.
    - O Apêndice C diz "(Tabelas 5 e 6 e Figuras 3 e 4)", mas a Figura 5 também deriva desses arquivos.
16. **Lacuna já conhecida em 21/09 e ainda aberta.**
    - **Situação:** o bloco 5 de limitações (levantamento bibliográfico e desvio temporal) é o único sem item correspondente no bloco de consolidação da §6.5.
    - **Correção:** acrescentar um item 7, "(bloco 5)", com a expressão de busca complementar do Apêndice A.1 e a caracterização de desvio.

---

## 3. Pendências do autor (fora do texto, inalteradas desde 21/09)

1. Data e assinatura do Anexo A na versão de depósito.
2. Etiqueta/release do commit avaliado, remoção e rotação das credenciais, publicação do submódulo `web`, arquivamento no Zenodo (opcional).
3. Depósito do script que gera `data/c6_ocr_benchmark_*.csv`. Resolver o K-1 exige, no mínimo, os CSVs locais, que existem.
4. Correção do registro `epochs`/`lr` do ByT5 no MLflow.
5. Conferência do nome e do título da coordenadora nos Agradecimentos (já grafado "Profa. Dra. Solange Oliveira Rezende").
6. Turnitin sobre o corpo do texto antes do depósito (MBA L8).

---

## 4. Ordem sugerida

1. **K-1:** Quadro 5, Quadro 1 e §5.5.3.
2. **M-1 a M-4:** texto; cerca de 30 min no total.
3. **M-5 e M-6:** Apêndice C e §4.9.
4. **M-7** e os itens **LEVE 1–3**: ficha, cabeçalho e `.bib`; exigem recompilar com `bibtex`.
5. Demais itens LEVE.
