# Validação da monografia contra o conteúdo das aulas do MBA

**Monografia:** *Solução para extração e classificação em faturas de cartão de crédito utilizando ferramentas de inteligência artificial* — Luiz Henrique Monteiro Silva Lima
**Fonte de verificação:** 605 aulas/tutorias transcritas do MBA em IA e Big Data (ICMC/USP), com foco em MET I–IV (Metodologia e Projeto — Profas. Juliana Moraes e Solange Rezende), Ciência de Dados/AM (Prof. Ricardo Marcacini), Estatística (Profa. Cibele Russo), PLN e Mineração de Textos (Prof. Marcacini e tutores), Governança de Dados (Profa. Marcela e Prof. Javam) e Processamento Analítico (Lakehouse).
**Versão verificada:** `docs/TCC - Final/` (commit `6896aa6`, 18/09/2026, 130 páginas).
**Data:** 18/09/2026.

Este relatório **não repete** os achados dos relatórios anteriores (Prof. Ciferri, 08/07/2026; revisão de 17/09/2026, já aplicada). Ele cruza a monografia com o que os professores do programa efetivamente ensinaram e cobram, e aponta onde o texto diverge disso ou onde uma técnica ensinada no curso resolveria uma limitação registrada.

**Marcadores:** **CRÍTICO** (afeta a lógica da defesa) · **MODERADO** (recomenda-se corrigir) · **LEVE** (ajuste fino) · **POSITIVO** (mérito alinhado ao curso).

---

## 1. Sumário executivo

A monografia está acima do que as disciplinas de metodologia exigem: o protocolo experimental (teste cego por estabelecimento, IC por *bootstrap*, teste de McNemar, ablação, MLflow) vai além do que o módulo de AM ensina (validação cruzada estratificada e *holdout*), e a honestidade em refutar a própria hipótese é exatamente o que a Profa. Juliana pede ("se o resultado não foi o desejado, ainda assim é pesquisa; relate o que de fato chegou").

Há, porém, **três pontos que a banca pode explorar na defesa** e que decorrem diretamente do conteúdo das aulas:

| Id | Achado | Aula que fundamenta | Onde corrigir |
|----|--------|---------------------|---------------|
| C1 | H1a é declarada **sustentada** por um modelo (Naive Bayes) que **não é o objeto da hipótese** (a esteira híbrida com agente), e a sustentação é estatisticamente marginal (p = 0,049; IC 95% da acurácia inclui 85%). | MET I aula 2 (hipótese guia o trabalho e é verificada sobre o que se propôs); Estatística — testes de hipótese, IC. | Cap. 4 §4.2; Cap. 5 §5.8; Resumo; Cap. 6 §6.3 |
| C2 | O ramo chamado de **RAG** não faz *augmented generation*: o LLM nunca recebe os vizinhos recuperados. Pelo conceito ensinado no curso (e por Lewis et al., 2020, citado), é busca vetorial com roteamento, não RAG. | Mineração de Textos aula 10 (LLMs) e tutoria de PLN sobre RAG/few-shot (21/03/2026). | Terminologia em todo o texto; ou implementar (experimento barato) |
| C3 | A Introdução **antecipa o resultado** ("Adianta-se ao leitor que… a hipótese central é refutada"). A Profa. Juliana é explícita: resultado aparece no resumo e na conclusão, nunca na introdução. | MET IV tutoria 16/06/2026. | `USPSC-Cap1-Introducao.tex:64` |

Nenhum dos três exige novo experimento; C2 admite um experimento opcional de baixo custo que ataca o principal gargalo medido (acurácia condicional de 21% do ramo LLM).

---

## 2. O que está alinhado com o curso (preservar)

- **[POSITIVO] Estrutura e roteiro.** Seis capítulos com Considerações Iniciais/Finais, questões de pesquisa e hipótese no Cap. 4, validação no Cap. 5 — exatamente o roteiro cobrado pelo orientador, que prevalece sobre a orientação genérica de MET I (introdução corrida sem subseções).
- **[POSITIVO] Escrita no passado, impessoal, siglas definidas na primeira ocorrência, estrangeirismos em itálico com equivalente em português** — checklist de MET II aula 1 atendido.
- **[POSITIVO] Correspondência 1:1 entre citações e referências** (56 chaves citadas = 56 entradas no `.bbl`; zero *undefined citation* no log). É a regra "o número de autores citados tem de ser idêntico ao número de referências" (MET IV tutoria 23/06).
- **[POSITIVO] Intercorrências relatadas** (DuckDuckGo indisponível, HITL simulado, validação incorporada ao treino, parâmetros do LLM não registrados) — MET II/IV pedem que "se um teste falhou, informe".
- **[POSITIVO] Declaração de uso de IA** preenchida no formulário oficial do programa, com ferramenta nomeada, nível 3 assinalado e declaração de responsabilidade — obrigatoriedade anunciada em MET IV tutoria 23/06.
- **[POSITIVO] Métrica primária declarada antes da avaliação (F1-Macro) e justificada pelo desbalanceamento** — Ciência de Dados aula 11 ensina que "acurácia não deve ser aplicada em dados desbalanceados".
- **[POSITIVO] Uso do teste não paramétrico correto** (McNemar, pares discordantes 11/23 e 17/17, esperados ≥ 5, logo a aproximação χ² é válida — Estatística, testes não paramétricos parte 1).
- **[POSITIVO] Escolha de LLM local, aberta e pequena por LGPD** — recomendação recorrente nas tutorias de PLN ("rodar local por conta da LGPD, com modelos pequenos").
- **[POSITIVO] Figuras com eixo iniciando em zero, sem 3D, cores distinguíveis** — Visualização de Dados aula 3 (eixo truncado, *chart junk*, pizza).
- **[POSITIVO] Referências recentes** (2024–2026: 14 de 56) combinadas com fundadoras — MET I tutoria 28/11: "a área de vocês é revolucionária; literatura de 10 anos atrás não serve para tudo".

---

## 3. Achados críticos

### C1 — Veredito de H1a incoerente com o objeto da hipótese e estatisticamente marginal

**Onde:** `USPSC-Cap3-Metodologia.tex:21-33` (hipótese), `USPSC-Cap4-Avaliacao_Experimental.tex:707` (veredito), Resumo, Cap. 6 §6.3.

**O que o curso ensina.** MET I aula 2: a hipótese é a "resposta provisória" ao problema e "vai ser confirmada ou não ao final"; MET IV tutoria 16/06: "erro grave é levantar hipótese sobre método/ferramenta que você não se propôs a estudar" — o inverso também vale: verificar a hipótese com um artefato que ela não menciona. Estatística (inferência e testes de hipótese): conclusão sobre a população exige IC ou teste, não apenas a estimativa pontual.

**O que a monografia faz.** A hipótese central afirma que *"uma esteira híbrida que integra normalização léxica, busca vetorial (pgvector), agente LLM com ferramentas e HITL"* atinge acurácia e F1-Macro > 85%. O veredito de H1a ("SUSTENTADA") usa o **TF-IDF + Naive Bayes (88,3%)**, que é uma linha de base, não a esteira híbrida. A esteira híbrida (Agente) obteve 61,4% de acurácia e 60,0% de F1-Macro — ou seja, **H1a e H1b são ambas refutadas para o objeto declarado da hipótese**.

Além disso, mesmo tomando o Naive Bayes, a sustentação é marginal. Recalculado a partir de `resultados/predicoes__tfidf_naive_bayes.csv` (295 acertos em 334):

| Modelo | Acertos | Acurácia | IC 95% (Wilson) | Teste binomial exato, H0: acc ≤ 85% |
|---|---|---|---|---|
| TF-IDF + NB | 295/334 | 88,3% | **[84,4%; 91,3%]** | **p = 0,049** |
| TF-IDF + RF | 283/334 | 84,7% | [80,5%; 88,2%] | p = 0,59 |
| RAG (norm.) | 283/334 | 84,7% | [80,5%; 88,2%] | p = 0,59 |
| RAG (bruto) | 276/334 | 82,6% | [78,2%; 86,3%] | p = 0,90 |
| Agente | 205/334 | 61,4% | — | p ≈ 1 |

O IC da única arquitetura acima do limiar **inclui 85%**, e o p-valor fica a 0,001 do nível de significância. A monografia aplicou *bootstrap* e McNemar ao F1-Macro, mas nenhum IC ou teste à acurácia — justamente a métrica que sustenta o único veredito favorável.

**Recomendação (sem novo experimento).**
1. Em §5.8, verificar H1a e H1b **para a esteira híbrida** (ambas refutadas: 61,4% / 60,0%), e em parágrafo separado reportar que a melhor arquitetura avaliada (NB) supera o limiar de acurácia apenas marginalmente (p = 0,049; IC 95% [84,4%; 91,3%]) e fica 21,7 p.p. abaixo do limiar de F1-Macro.
2. Alternativa, se o orientador preferir manter o veredito por "qualquer arquitetura da esteira": reformular em §4.2 o objeto da hipótese para "um classificador da esteira" e declarar explicitamente que a verificação toma a melhor das cinco arquiteturas. Em qualquer caso, incluir o IC e o teste da acurácia (o script `09_rag_norm_significancia.py` já tem a infraestrutura de reamostragem).
3. Ajustar Resumo, Abstract e §6.3 em conformidade.

Isso também neutraliza a pergunta mais provável da banca (MET IV aula inaugural, Profa. Solange: *"Qual o seu baseline? O modelo que você propôs ganhou desse baseline?"*). A resposta honesta — não ganhou — já está no texto; falta que o veredito formal da hipótese diga a mesma coisa.

### C2 — "RAG" sem *augmented generation*

**Onde:** Tabelas 7, 8, 9, 10, 12 e 13 ("Busca Vetorial RAG"), §2.2.3 ("mecanismos de RAG, onde exemplos canônicos rotulados são recuperados dinamicamente para subsidiar a tomada de decisão do classificador"), Resumo (palavra-chave "Geração aumentada por recuperação").

**O que o curso ensina.** Mineração de Textos aula 10: RAG é "a construção de *prompts* de maneira dinâmica… injetando a base de conhecimento dentro da instrução, de maneira que a LLM dá a resposta já considerando a base injetada". Tutoria de PLN (21/03/2026): "com o RAG quero que ela responda em cima dos documentos que eu tenho"; *few-shot* = "colocar exemplos dentro do *prompt*". Mesma definição de Lewis et al. (2020), citado na monografia.

**O que o código faz.** `notebooks/modules/nodes.py:144-183` (`classificar_com_llm`): o *system prompt* contém regras e a lista de categorias; a mensagem humana é apenas `"Classifique esta transação: {descrição}"` (`05_agente.py:155`). `buscar_por_similaridade` recupera k = 3 vizinhos, usa só o primeiro para roteamento e **descarta os três antes de chamar o LLM**. O modelo de linguagem opera em *zero-shot* sem nenhuma evidência recuperada. Não há geração aumentada por recuperação em ponto algum da esteira.

**Por que importa.** (i) Terminologia: o Prof. Marcacini (banca provável ou leitor da área) reconhece a diferença de imediato. (ii) Substância: a monografia identifica o ramo LLM como o gargalo (acurácia condicional 21,4%, abstenção sistemática para "Despesas Diversas") e lista como causas possíveis "modelo, *prompt* ou ferramenta de busca". A causa mais óbvia pelo conteúdo do curso — **o LLM decide sem ver os exemplos rotulados mais próximos** — não está entre as hipóteses listadas.

**Recomendação.**
- Mínimo (texto): renomear a arquitetura para "Busca vetorial densa (pgvector + MiniLM)" nas tabelas e no texto; reservar o termo RAG para a §2.2.3 como conceito, com uma frase explícita de que a esteira **não** injeta os vizinhos no *prompt*; retirar "Geração aumentada por recuperação" das palavras-chave ou qualificá-la. Acrescentar essa ausência à lista de causas candidatas em §5.6.4 e §6.4 (item 5).
- Opcional (experimento barato, ~160 transações × ~7 s ≈ 20 min): passar ao *prompt* os 3 vizinhos com categoria e similaridade ("Exemplos semelhantes já classificados: …") e reexecutar apenas o ramo LLM sobre as mesmas 334 transações. É a técnica *few-shot* da aula 10 aplicada ao dado que a esteira já recupera. Se o ganho for relevante, o item 4 dos trabalhos futuros ganha um resultado; se não for, a conclusão "gargalo no raciocínio" fica muito mais forte.

### C3 — Antecipação do resultado na Introdução

**Onde:** `USPSC-Cap1-Introducao.tex:64` ("Adianta-se ao leitor que… a hipótese central… é **refutada**").

**O que o curso ensina.** MET IV tutoria 16/06/2026 (Profa. Juliana, em vermelho no slide): *"não é na introdução que vocês vão antecipar o resultado de trabalho, de nenhum trabalho, nem de TCC, nem de mestrado, nem de doutorado. O resultado vocês vão apresentar no resumo, por uma questão de regra, e depois somente no próprio capítulo de conclusão."*

**Observação.** A revisão de 17/09 tratou isso como problema de alocação (item I12) e sugeriu mover o parágrafo. Pelo que a professora de metodologia do programa ensina, o parágrafo deve **sair** da Introdução. O leitor já encontra o resultado no Resumo (linha 15) e em §5.8/§6.3. Se o orientador fizer questão de um aviso precoce, a forma aceitável é uma única frase neutra ao final do escopo ("a hipótese é verificada formalmente na Seção 5.8"), sem o veredito.

---

## 4. Achados moderados

### M1 — Metadado de origem fixo em "C6" para todas as transações do teste cego (inclusive as 100 do Nubank)

**Onde:** `notebooks/experimentos/05_agente.py:154` (`"source": "bronze/source=c6/…/original.csv"` codificado para todo o laço de teste) → `nodes.py:163` injeta `Banco Origem: c6` no *prompt* do LLM. No modo de produção (`rodar_gravar`, linha 228) o `source` é o real; o problema é só na avaliação.

**Impacto no texto.** (i) §5.6.2 conclui que o ramo LLM cai de 22,7% (C6) para 12,8% (Nubank) e diz não conseguir isolar a causa — há um confundidor não declarado: o LLM foi informado de origem errada para todo o subconjunto Nubank. (ii) Q4 pergunta sobre "injeção de metadados contextuais (origem do arquivo…)"; a resposta a Q4 em §5.8 não menciona que o metadado de origem esteve incorreto em 30% do teste, logo esse componente da Q4 não foi efetivamente avaliado.

**Recomendação.** Registrar em §5.2 (intercorrências) e em §6.5, e retirar da Resposta a Q4 qualquer inferência sobre o metadado de origem. Opcionalmente reexecutar só o ramo LLM com `source` correto (mesmo custo do experimento de C2; os dois podem ser combinados).

### M2 — Texto afirma que "somente o agente consumiu o texto integralmente normalizado"; o LLM recebeu a descrição bruta

**Onde:** Tabela 7, fonte (`Cap4:338`); §5.6, item 5 e nota de rodapé.

O nó `normalizar` produz `nome_normalizado`, usado pela busca vetorial. A mensagem enviada ao LLM é construída com `row['descricao']` (bruta). Assim, dentro do agente, o ramo vetorial viu texto normalizado e o ramo LLM viu texto bruto (mais o *system prompt* com regras de *gateway*). Corrigir a frase para refletir isso; a ablação da normalização (§5.6.4) não é afetada.

### M3 — LGPD: artigo citado errado, distinção anonimização/pseudonimização e ausência de base legal

**Onde:** `USPSC-Cap3-Metodologia.tex:249-252`; Quadro 1 ("amostra… anonimizada"); §4.4 (dados de dois portadores).

**O que o curso ensina.** Governança — tutoria 14/01/2026 (Profa. Marcela): *"a gente não precisa de consentimento para tudo, mas a gente precisa **sempre** de uma base legal"* (arts. 7º e 11); tutoria 21/01: dado com identificador substituível "a LGPD **não** considera anonimizado; é outra categoria, pseudonimizado, e a LGPD continua se aplicando"; pesquisa acadêmica tem isenção **parcial** (art. 4º, II, b) mas "os princípios e a definição de uma base legal continuam se aplicando".

**Problemas no texto.**
1. **"Minimização do Cadastro do Titular (Art. 13)"** — o art. 13 da Lei 13.709/2018 trata de *estudos em saúde pública por órgãos de pesquisa*; o que o item descreve (titular referenciado só por identificador interno, identidade mantida em outro sistema) é a definição legal de **pseudonimização** (art. 13, § 4º). Renomear o item para "Pseudonimização do titular (art. 13, § 4º)" e deixar claro que as tabelas transacionais são pseudonimizadas, não anonimizadas — exatamente a distinção que o curso cobra.
2. **Item 1** chama o princípio do art. 6º, III de "minimização"; o nome legal é **necessidade** (a lei não usa "minimização"). Ajuste de precisão.
3. **Base legal ausente.** A seção não diz sob qual hipótese do art. 7º os dados dos dois portadores foram tratados. Sugestão de parágrafo: tratamento realizado para fins exclusivamente acadêmicos (art. 4º, II, b), aplicando-se os arts. 7º e 11; base legal: consentimento do titular (art. 7º, I) — o autor é um dos portadores e o segundo portador consentiu expressamente com o uso das faturas para esta pesquisa; nenhum dado sensível (art. 5º, II) é tratado, pois descrições de estabelecimento não revelam origem racial, saúde, etc. (se alguma categoria — "Saúde" — puder ser lida como inferência sobre saúde, vale uma frase de ressalva).
4. Quadro 1 chama a amostra de "anonimizada"; nomes de estabelecimento não são dados pessoais do titular, então o adjetivo é desnecessário e tecnicamente impreciso — "amostra real" basta.

### M4 — Conclusão com 10 páginas e re-discussão de resultados

**Onde:** Cap. 6 (pp. 99–108).

**O que o curso ensina.** MET IV tutoria 16/06: conclusão "do específico para o geral", "no máximo, mas no máximo mesmo estourando, duas páginas", "não é na conclusão que se discute resultado; a discussão é no capítulo de análise". O roteiro do orientador exige subseções (síntese, objetivos, limitações, trabalhos futuros), então duas páginas não são viáveis — mas dez é o dobro do razoável.

**Recomendação.** Alvo de 5–6 páginas: (a) fundir §6.2 e §6.3 (as contribuições e o confronto com objetivos repetem-se); (b) reduzir §6.4 de nove conclusões para as quatro ou cinco que são de fato conclusões (itens 2, 3, 5, 8 e 9), pois os demais reexplicam números do Cap. 5; (c) em §6.5, manter uma linha por limitação com remissão à seção do Cap. 5 onde ela já está discutida — hoje itens 3, 4, 6, 7, 9 e 10 reproduzem parágrafos inteiros do Cap. 5.

### M5 — "Data Lakehouse" acima do que foi implementado

**Onde:** §4.5, Figura 1, Resumo.

**O que o curso ensina.** Processamento Analítico (aula 1, parte 10): Lakehouse = "estruturas e recursos de gerenciamento semelhantes aos de *data warehouse* diretamente sobre armazenamento de baixo custo em **formatos abertos**", com **transações ACID**, suporte a esquemas de DW, lote + *streaming*, governança e armazenamento desacoplado da computação.

**O que existe.** Bronze em MinIO (data lake) + PostgreSQL/pgvector (relacional) + Kafka + MLflow. Não há formato de tabela aberto com ACID sobre o objeto (Delta/Iceberg foram removidos por excederem o escopo, corretamente), e Silver/Gold não estão materializadas — o próprio Cap. 6 diz isso. Chamar o conjunto de "Data Lakehouse" convida a pergunta "quais propriedades de lakehouse a sua solução atende?".

**Recomendação.** Qualificar uma vez em §4.5: "arquitetura em camadas inspirada no paradigma *Lakehouse* (Armbrust et al., 2021), da qual esta pesquisa implementa a camada Bronze em armazenamento de objetos e a camada Silver em banco relacional; as propriedades de formato aberto transacional e de consumo analítico são apontadas como evolução (Cap. 6)". Manter o termo nas figuras é aceitável depois dessa ressalva.

### M6 — Desbalanceamento: técnica descrita e não usada; nenhuma técnica de balanceamento ensinada no curso foi testada

**Onde:** §2.2.4.1 (`Cap2:57`: "*Complement Naive Bayes* … particularmente adequada aos cenários de cauda longa observados neste trabalho") vs. Tabela 4 e `02_baselines.py:19,57` (`MultinomialNB` padrão).

**O que o curso ensina.** Ciência de Dados aulas 9 e 31 (dados desbalanceados / balanceamento): sobreamostragem, subamostragem, SMOTE e pesos de classe como resposta padrão ao desbalanceamento; aula 11: acurácia balanceada.

A monografia identifica o desbalanceamento e a cauda longa como a principal causa do F1-Macro baixo (§5.6.1, §6.5 item 5), mas só o Random Forest recebeu tratamento (`class_weight`). O Naive Bayes usa a variante que a própria fundamentação diz ser inadequada ao caso; nenhuma reamostragem foi tentada. Um leitor do módulo de AM perguntará "por que não SMOTE/oversampling ou *Complement NB*, que o curso ensina e a fundamentação recomenda?".

**Recomendação.** Duas saídas, ambas baratas: (a) trocar `MultinomialNB` por `ComplementNB` (uma linha; segundos de execução) e reportar; ou (b) manter e retirar da §2.2.4.1 a frase que recomenda a variante complementar, registrando em §6.5 que técnicas de balanceamento (SMOTE, *oversampling*, *Complement NB*) não foram avaliadas. A opção (a) também alimenta o item 3 dos trabalhos futuros.

### M7 — Validação cruzada com vazamento quando o curso e a monografia dispõem da alternativa agrupada

**Onde:** §5.6, item 2 e Tabela 9 (CV 5-fold `StratifiedKFold` vs. teste cego).

A monografia apresenta a diferença CV–teste cego (23–25 p.p.) como sua contribuição metodológica principal. Ciência de Dados aula 17 ensina que a CV existe "para estimar generalização em exemplos que o modelo ainda não conhece". A forma de obter uma CV **sem** memorização de estabelecimentos é `StratifiedGroupKFold(groups=estabelecimento)` — mesma partição por grupo que o teste cego já usa, mas com cinco estimativas e desvio-padrão. Custo: segundos, para as duas linhas de base esparsas. Com isso a Tabela 9 ganharia uma terceira coluna ("CV agrupada por estabelecimento") que confirma, dentro do próprio treino, que a queda é efeito de memorização e não de peculiaridade dos 334 exemplos do teste. Sem isso, o achado principal apoia-se em uma única partição.

### M8 — Modelo de *embeddings* genérico sem ajuste fino, quando o curso ensina o ajuste

**Onde:** §2.2.3, §5.6 item 4, §6.6.

Mineração de Textos aula 6: o SBERT que gera boas *embeddings* de similaridade é um BERT com **ajuste fino em pares anotados** (STS); "nada impede que vocês aprendam sua própria representação com o *corpus* da organização"; a disciplina inclui aula prática de *fine-tuning* de Sentence-Transformers. A monografia usa `paraphrase-multilingual-MiniLM` treinado para paráfrase genérica, aplicado a nomes de estabelecimento truncados — domínio para o qual não foi ajustado — e conclui que a busca densa "ficou limitada pela base fria". O ajuste fino contrastivo em pares (descrição, descrição) do mesmo estabelecimento/categoria, com os 1.326 exemplos de treino, é o trabalho futuro mais natural pelo conteúdo do curso e não aparece na lista de §6.6.

---

## 5. Achados leves

- **L1 — Acurácia balanceada.** A "Revocação Macro" (Equação 5.4) **é** a acurácia balanceada que a aula 11 recomenda para dados desbalanceados. Nomeá-la assim (uma vez) e usá-la na discussão de H1a fortalece o argumento de que a acurácia global não é a métrica adequada.
- **L2 — Recomendação prática ausente.** O programa é um MBA; a Profa. Solange pergunta "o que significam esses resultados para o problema que você está resolvendo?". Cabe um parágrafo em §6.4 ou §6.7 com a recomendação de engenharia que decorre dos dados: classificador esparso (TF-IDF + RF) como primeira linha; busca vetorial para estabelecimentos já vistos (98% de acurácia condicional); LLM restrito aos casos residuais com confirmação humana; ByT5 não recomendado neste volume.
- **L3 — LLM pequeno como cérebro do agente.** Mineração de Textos aula 17 (agentes): "com LLMs menores o agente fica perdido… é muito recomendável usar uma LLM de bastante capacidade; é interessante comparar com uma proprietária para ver a diferença". A monografia chega à mesma constatação, mas a lista de causas não isoladas (§6.4 item 5) ganharia uma frase explicitando que o tamanho do modelo (4B efetivos) é a explicação mais alinhada à literatura de agentes, e o experimento de trocar apenas o modelo local (por um de 12–27B) nas ~160 transações roteadas ao LLM custa cerca de uma hora.
- **L4 — Figura 8 (F1 por categoria):** a linha tracejada de 85% não é explicada na legenda nem na fonte; e o suporte por categoria (4 a 5 exemplos nas classes com F1 = 0) merece anotação na barra, pois é o argumento central de §5.6.3.
- **L5 — Objetivos específicos** ainda trazem detalhe de ferramenta ("Docling", "LangGraph", "Naive Bayes e Random Forest… TF-IDF"). MET I aula 2: objetivos são "ações menores" em infinitivo; a tecnologia pertence ao capítulo de solução. Já apontado em 17/09 (I10); reforço porque MET I é explícita.
- **L6 — "As soluções atualmente disponíveis…" (Cap1:42)** sem citação. MET IV tutoria 16/06: "mesmo dados de senso comum precisam ser citados". Como o Cap. 3 revisa trabalhos acadêmicos e não produtos, trocar por "as abordagens descritas na literatura (Capítulo 3)".
- **L7 — Declaração de IA como Anexo.** A Profa. Juliana descreve a declaração como **apêndice** assinado pelo aluno (23/06). O formulário é do programa, mas o conteúdo preenchido e assinado é do autor; se o modelo ICMC/MBA não determinar o contrário, apêndice é a alocação coerente com a orientação. Confirmar com o orientador; sem impacto na nota.
- **L8 — Antes do depósito:** MET IV recomenda passar o corpo do texto (sem pré-textuais, referências e apêndices, para não inflar o índice) no Turnitin da USP, em blocos, 3 submissões por 24 h. Prazo de entrega da monografia à banca: 10 dias antes da defesa; 21 dias após a defesa para a versão corrigida.

---

## 6. Perguntas prováveis da banca (derivadas das aulas) e onde a resposta está — ou falta

| Pergunta | Base no curso | Situação |
|---|---|---|
| "A hipótese fala da esteira híbrida; você a sustenta com o Naive Bayes?" | MET I aula 2 | **Falta** — ver C1 |
| "Onde está a geração aumentada por recuperação, se o LLM não recebe os vizinhos?" | Min. Textos aula 10; PLN tutoria RAG | **Falta** — ver C2 |
| "Por que não usou SMOTE/oversampling/pesos de classe, já que o problema é desbalanceamento?" | Ciência de Dados aulas 9, 11, 31 | **Falta** — ver M6 |
| "Por que a CV não foi agrupada por estabelecimento?" | Ciência de Dados aula 17 | **Falta** — ver M7 |
| "Qual a base legal do tratamento dos dados do segundo portador?" | Governança tutoria 14/01 | **Falta** — ver M3 |
| "O que a sua solução tem de *lakehouse*?" | Proc. Analítico aula 1 | Parcial — ver M5 |
| "Sua proposta ganhou do *baseline*? O que recomenda na prática?" | MET IV aula inaugural | Presente em §6.4, mas sem recomendação explícita — ver L2 |
| "A diferença de 2,5 p.p. entre RF e RAG é real?" | Estatística — testes | **Presente** (McNemar p = 0,86) |
| "Por que F1-Macro e não acurácia?" | Ciência de Dados aula 11 | **Presente** (§5.4.2) |
| "Como você usou IA na escrita?" | MET IV tutoria 23/06 | **Presente** (Anexo A) |

---

## 7. Ordem sugerida de correção

1. C1 (veredito da hipótese + IC/teste da acurácia) — texto, ~1 h.
2. C3 (retirar antecipação da Introdução) — 5 min.
3. C2 texto (renomear RAG e acrescentar a causa candidata) — 30 min; experimento opcional — ~1 h com M1.
4. M3 (LGPD: art. 13 §4º, necessidade, base legal) — 30 min.
5. M2 e M1 (precisão sobre o que cada ramo consumiu; `source` fixo) — 20 min.
6. M4 (enxugar Cap. 6) — 2 h.
7. M6/M7 (Complement NB e CV agrupada) — 30 min de execução se optar por rodar; senão, 15 min de texto.
8. M5, L1–L8 — ajustes pontuais.

Os itens 1–5 são os que mudam a leitura da banca; os demais elevam a consistência com o que o programa ensina.
