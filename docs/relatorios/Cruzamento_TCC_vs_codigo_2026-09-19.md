> **Status (19/09/2026):** as correções de texto listadas abaixo foram aplicadas na monografia (Cap. 1, 2, 4, 5, 6, Resumo, Abstract e Apêndices B, C, D e E), junto com os itens C1–C3, M1–M5 e L1–L6 do relatório de 18/09. Itens marcados como "ajustar o código" foram descritos no texto como limitações/trabalho futuro; o código não foi alterado, exceto pela nova etapa `notebooks/experimentos/11_ic_acuracia.py` (IC de Wilson e teste binomial da acurácia, contagem de ancoramento e métricas do run com busca web).

# Cruzamento monografia × código-fonte (19/09/2026)

Base analisada: `docs/TCC - Final/` (Cap. 1, 4, 5, 6, Apêndices B a E) versus `service-ingestao/`, `worker-prata/`, `notebooks/modules/`, `notebooks/experimentos/`, `service-classification/`, `infra/` e o submódulo `web`.

## 1. Divergências arquiteturais e de fluxo

**1.1 Figura da arquitetura (Cap. 4, `fig:arquitetura_mlops`) não corresponde ao fluxo real.** A figura mostra o Worker de Extração gravando "Textos Sujos" no bucket `bronze-txt`, o agente sendo disparado pelo Kafka ("Dispara Grafo") e consumindo dados do `bronze-txt`. No código, `worker-prata/app.py` consome o tópico Kafka e grava direto no PostgreSQL (`faturas`/`transacoes`, via `worker-prata/modules/parsers.py` e `bitparser.py`). Nenhum código escreve em `bronze-txt`; o bucket só é criado em `infra/scripts/setup_minio.sh:18`. O agente não tem consumidor Kafka: ele é executado manualmente em lote por `notebooks/experimentos/05_agente.py --gravar`, que seleciona `transacoes` com `status_classificacao='pendente'`.

**1.2 Tesseract não está integrado à esteira de extração.** O texto (Seção "Esteira de ingestão e extração híbrida", Tabela de tecnologias, contribuição 1 do Cap. 6) descreve um fluxo em três etapas com Tesseract OEM 3 / PSM 6 e filtro de confiança > 40 %, "integrado ao grafo de decisão da camada de extração". No `worker-prata` não há importação de `pytesseract`; `worker-prata/modules/service_ocr.py:47` define `do_ocr = False`, ou seja, o Docling nunca executa OCR algum (nem o RapidOCR configurado logo abaixo). A função com Tesseract (`extrair_texto_avancado`, `notebooks/modules/utils.py:126`) existe, mas só é chamada em notebooks (`data_analysis.ipynb`, `tesseract_ocr.ipynb`), nunca pelo worker nem pelo grafo. Não existe roteamento "se o conversor não identifica tabelas, aciona-se o Tesseract".

**1.3 Ordem e semântica do metadado `is_digital_nativo` invertidas para PDF.** O texto diz que CSV/OFX/JSON desativam hipóteses de OCR e "imagem ou PDF escaneado" as ativam. Em `notebooks/modules/utils.py:91` a lista de nativos é `['.csv', '.ofx', '.json', '.txt', '.xml']`: todo PDF, inclusive os PDFs nativos digitais do C6/Nubank que são a entrada principal, recebe a instrução "considere erros de OCR". Além disso, no teste cego `05_agente.py:154` fixa `source` em `bronze/source=c6/.../original.csv` para as 334 transações, inclusive as 100 do Nubank. O metadado de origem foi, portanto, constante e parcialmente incorreto durante toda a avaliação, o que esvazia a parte "origem do arquivo" da Q4.

**1.4 A base vetorial consultada pelo agente não é a tabela apresentada no Apêndice B.** O apêndice apresenta `estabelecimentos.embedding VECTOR(384)` com índice `ivfflat` como "base de conhecimento e embeddings". O agente consulta a coleção LangChain `baseconhecimento` (tabelas `langchain_pg_collection`/`langchain_pg_embedding`, `notebooks/modules/async_service.py:23-54`; `nodes.buscar_por_similaridade`). `salvar_vectorstore` escreve apenas na coleção LangChain; `estabelecimentos` só é populada por `04_rag_pgvector.py --persistir-bd`. As duas bases divergem a cada execução. O nó `buscar_estabelecimentos` (cache exato em `estabelecimentos`) existe em `nodes.py` mas não é ligado ao grafo.

**1.5 Índice e tipos do Apêndice B não batem com os scripts SQL.** `infra/scripts/base.sql:57` cria índice `hnsw (m=16, ef_construction=64)`, não `ivfflat (lists=100)`; colunas são `REAL`/`TIMESTAMP` e não `NUMERIC(4,3)`/`TIMESTAMP WITH TIME ZONE`. O apêndice reproduz o ORM (`model.py`), não o esquema físico executado. A tabela `langchain_pg_embedding`, a que de fato é consultada, não recebe índice algum nos scripts.

**1.6 Roteamento de marketplace está quebrado para Mercado Livre e a função documentada não é usada.** Em `nodes.py:451` `eh_marketplace = estabelecimento in MARKETPLACES_AMBIGUOS`, onde `estabelecimento` vem de `detectar_estabelecimento` e retorna `"mercado livre"` com espaço, enquanto a chave do dicionário é `"mercado_livre"`. Resultado: Mercado Livre, o marketplace mais frequente no Brasil, nunca é roteado para `buscar_historico_marketplace`. A função `detectar_marketplace` (`nodes.py:102`), que o Apêndice E afirma ser usada "para sinalizar transações", não é chamada em lugar nenhum.

**1.7 O histórico de marketplace nunca "enriquece o contexto".** O texto afirma que o nó recupera preferências "no mesmo marketplace" e que "o resultado enriquece o contexto". `buscar_historico_marketplace` (`nodes.py:344`) filtra só por `usuario_id`, sem `estabelecimento_id`, e devolve `historico_marketplace`, chave que nenhum nó posterior lê: `classificar_com_llm` não a injeta no prompt. A função que a consumiria, `classificar_marketplace_por_historico`, lê outra chave (`historico_marketplaces`, com "s") e não está no grafo.

**1.8 `estruturar_saida_llm` não usa `with_structured_output` como via principal.** O texto diz que o nó "utiliza o método `with_structured_output` com validação Pydantic". O código (`nodes.py:188-338`) primeiro extrai um JSON por regex do texto livre; só se falhar chama `with_structured_output`; se isso falhar, faz uma segunda chamada ao LLM com um prompt de extração. Em seguida `_ancora_cat` (`nodes.py:229`) mapeia rótulos desconhecidos por `difflib` com corte 0,6 e, sem casamento, cai em "Despesas Diversas / Outros"; `05_agente.py:200` aplica um segundo ancoramento (`rapidfuzz` WRatio ≥ 55, senão "Despesas Diversas / Outros").

**1.9 HITL "genuíno em produção" não existe.** O Cap. 5 (Seção MLOps) e a limitação 7 do Cap. 6 dizem que em `rodar_gravar` o mecanismo "aguarda de fato a confirmação de um usuário". `05_agente.py:231` chama `_classificar_um(..., confirmar_hitl=False)`, que retoma o `interrupt` imediatamente com `confirmado=False` e grava status `sugerida`. O checkpointer é `MemorySaver` (`05_agente.py:115`), em memória do processo: nenhum outro processo, inclusive a aplicação web, consegue retomar a thread depois. Em nenhum dos dois modos o grafo espera um humano.

**1.10 A aplicação web não faz o que o texto atribui a ela.** O Apêndice C a descreve como "aplicação web de visualização orçamentária e confirmação humana (HITL)" e o Cap. 4 diz que "a visualização orçamentária ao usuário é atendida diretamente pela aplicação web sobre o PostgreSQL". O submódulo tem dois commits (`create-next-app` e "web"), login Logto, um sidebar e um componente de upload cujo envio é simulado (`FileUploadWithAttachment.tsx:45`, comentário "Simula o tempo da API"). Não há chamada à API de ingestão, acesso ao PostgreSQL, painel orçamentário nem tela de confirmação.

**1.11 Logto/RBAC não protege as APIs.** O texto diz que "o acesso aos pontos de acesso da API é protegido pelo servidor Logto via OIDC, com RBAC". `service-ingestao` (`RouterConfig.java`) expõe `POST /v1/datalake/bronze/upload` sem qualquer segurança e não depende de Spring Security; `service-classification` idem. Logto só faz login na web. Todos os parsers gravam `usuario_id=1` fixo, logo não há isolamento multi-inquilino.

**1.12 `log_classificacoes` nunca é escrita.** O texto (LGPD, Art. 46) diz que a tabela "mantém registro temporal auditável de todas as inferências". Nenhum código insere nela; só o ORM a modela e `10_verificacao_lgpd.py` a lê. O mesmo vale para `feedbacks`, `confirmacoes_categoria_marketplace` e `transacao_alocacoes_categoria`. O requisito não funcional de "registro rastreável de cada inferência" do Cap. 1 não é atendido.

**1.13 Autologging LangChain no MLflow e `results/raciocinio.txt` só existem em notebook legado.** `mlflow.langchain.autolog()` e `log_text(..., 'results/raciocinio.txt')` aparecem apenas em `notebooks/agent_v1.ipynb`. A esteira experimental (`05_agente.py`) registra apenas parâmetros e métricas agregadas via `registrar_resultado`; não há prompt, tokens nem cadeia de pensamento no MLflow.

**1.14 `service-classification/api.py` implementa outro modelo e outra abordagem.** A API usa `intfloat/multilingual-e5-large` em classificação zero-shot por similaridade texto–rótulo, sem base vetorial, sem agente e sem avaliação no Cap. 5. O texto afirma que o modelo de embeddings da solução é `paraphrase-multilingual-MiniLM-L12-v2` (384 d) e lista essa API apenas como "API de exposição do serviço de classificação".

**1.15 Escopo de formatos.** O Cap. 1 inclui OFX e JSON no escopo. `TipoArquivo.detectar` aceita só CSV e PDF; o worker descarta outros `content_type`. OFX/JSON existem apenas na heurística de `extrair_metadados_datalake`.

**1.16 Tabela de tecnologias.** `worker-prata` é descrito com "PyTesseract sobre Tesseract" (ver 1.2). A ingestão é descrita com "MinIO SDK 8.5.9", mas `MinioDatalakeAdapter`/`MinioConfig.java` usam o AWS SDK v2 (`S3AsyncClient`); a dependência `io.minio` está declarada e não é usada. O texto fixa Python 3.11, mas `requirements.txt` pina uma wheel `cp312` do PaddlePaddle e o `readme.md` cria o ambiente com `python=3.12`.

**1.17 Buckets.** O texto lista três buckets: `bronze-raw`, `bronze-txt` e `mlflow-artifacts`. `setup_minio.sh` cria `bronze-raw`, `bronze-txt`, `silver` e `mlops-dvc`; `mlflow-artifacts`, usado por `docker-compose-externalinfra.yml:56`, nunca é criado. O script ainda termina com comandos `pg_dump`/`docker cp`/`scp` que falham dentro do contêiner `mc`.

**1.18 Submódulo não registrado.** `web` é um gitlink (modo 160000) sem arquivo `.gitmodules`; `git clone --recurse-submodules`, instrução do Apêndice C, não baixa a aplicação web.

**1.19 A avaliação de OCR não está na esteira numerada.** O Apêndice C afirma que as etapas 01 a 10 geram "integralmente" os resultados do Cap. 5, "avaliação de OCR" inclusive. O benchmark Docling × Tesseract com `jiwer` está em `notebooks/data_analysis.ipynb` e produz `data/c6_ocr_benchmark_*.csv` (diretório `data/` ignorado pelo git).

**1.20 Duas rotinas de normalização diferentes.** `worker-prata/modules/parsers.py:66` (usada na ingestão para preencher `transacoes.nome_normalizado`) não tem a regra `tim*tim` documentada no Apêndice E; o agente recomputa com `utils.normalizar_nome`. E `estabelecimentos.nome_normalizado` é preenchida por `04_rag_pgvector.py` com `chave_estabelecimento` (só caixa baixa e acentos). Consequência: a busca `Estabelecimento.nome_normalizado == nome_est` em `salvar_resultado` raramente resolve `estabelecimento_id`.

## 2. Requisitos ou promessas não cumpridas

- **Ferramenta de busca web "não exercitada por ausência de conectividade".** O repositório contém um run completo com a ferramenta ligada (`resultados/agente_metricas_COMWEB.json`, `agente_teste_bruto_COMWEB.csv`, log de 08/09): 334 transações, acurácia 57,2 %, 48 erros de execução, 61 % vetorial. Os erros são `ConnectError` nos backends do `ddgs` (42 em `wikipedia.org/w/api.php`, 4 em `search.yahoo.com`, 1 `Server disconnected`). A ferramenta foi, portanto, exercitada e falhou; o run reportado é o `SEMWEB` (idêntico byte a byte a `agente_teste_bruto.csv`). A afirmação "não foi exercitado em nenhuma das 334 transações" e a justificativa "ausência de conectividade externa" são imprecisas.
- **Testes unitários com pytest:** `notebooks/pytest.ini` aponta para `tests`; `notebooks/tests/` está vazio. Não há um único teste Python. O único teste Java é `contextLoads()`. A Seção "Estratégia de garantia de qualidade" descreve testes de regex, parsers, aliases e contratos Pydantic que não existem.
- **Seed das 14 categorias canônicas:** `base.sql:151` insere 9 categorias com nomes diferentes (Compras, Lazer, Streaming, Serviços, Outros...). Nenhum script cria as 14 categorias que `common.py`, `nodes.py`, o prompt e `salvar_resultado` (lookup por nome) pressupõem. A reprodução a partir de `infra/` não funciona sem intervenção manual não documentada.
- **Fallback Tesseract** (1.2), **ingestão OFX/JSON** (1.15), **enriquecimento por histórico de marketplace** (1.7), **detecção de Mercado Livre** (1.6), **HITL com espera real** (1.9), **painel/HITL na web** (1.10), **RBAC nas APIs** (1.11), **log de auditoria** (1.12), **autologging LangChain** (1.13), **bucket `mlflow-artifacts`** (1.17), **submódulo** (1.18).
- **Aprendizado ativo cumulativo:** `04_rag_pgvector.py:75-79` apaga todas as coleções LangChain e `estabelecimentos` a cada execução com `--persistir-bd`. Toda retroalimentação feita por `salvar_vectorstore` é descartada quando a etapa 4 é reexecutada.
- **Hiperparâmetros do ByT5 registrados errado no MLflow:** `03_byt5.py:105` loga `epochs=18, lr=3e-4`, mas treina com `num_train_epochs=12, learning_rate=5e-4` (`03_byt5.py:65-66`). O texto (Tabela de hiperparâmetros) está correto; o "rastreamento integral no MLflow" contém parâmetros falsos.
- **Código morto que contradiz o texto:** `worker-prata/aimodules.py` instancia `claude-sonnet-4-6` via `init_chat_model` (API proprietária em nuvem) num agente aritmético de exemplo, dentro do serviço que o texto descreve como executado "sem dependência de APIs proprietárias".

## 3. Inconsistências conceituais e de nomenclatura

- **Limiar de persistência vetorial:** Cap. 4 e Quadro de arestas dizem "persiste somente se confiança > 0,85" (correto: `nodes.py:750`, `<= 0.85` retorna). A Seção MLOps do Cap. 5 diz "alta confiança (≥ 0,85)". Uniformizar para "> 0,85".
- **Latência do ramo LLM:** Cap. 5, Seção MLOps: "o ramo LLM local custou 6,5 s por transação". Os 6.529,97 ms são a média ponderada sobre as 334 transações (mediana 40 ms). A média condicional do ramo LLM é ≈ 13,7 s (6.530 ms ÷ 0,476). O Cap. 6 diz "dezenas de segundos". Corrigir a frase do Cap. 5.
- **`rota_apos_llm` em `nodes.py` ≠ roteador usado:** `nodes.py:542` roteia só por `requer_confirmacao`; `05_agente.py:75` (`rota_apos_estruturar`) usa `requer_confirmacao or conf <= 0.80`. O texto cita corretamente o segundo, mas o módulo reutilizável documentado no Apêndice C implementa outra regra.
- **Limiar 0,85 duplicado:** `AsyncService.SIMILARITY_THRESHOLD = 0.85` existe, mas `rota_apos_busca_vetorial` (`nodes.py:536`) usa o literal `0.85`. `services.retrivier` (sic) com `score_threshold=0.85` é criado e nunca usado.
- **Apêndice B:** `ivfflat lists=100` × `hnsw` no SQL; tipos numéricos e de data diferentes (1.5).
- **Apêndice E:** afirma que `detectar_marketplace` é usada; não é (1.6).
- **Split:** texto diz 69 / 11 / 20 % por transação; docstring de `common.split_estratificado` diz "70/15/15 estratificado". As proporções 70/15/15 valem por estabelecimento, não por transação. Ajustar docstring.
- **Quantidade de CSVs do C6:** `01_preparar_dados.py` diz "105 CSVs de fatura" e "27 CSVs Nubank"; o Cap. 5 fala em 49 CSVs oficiais do C6. Se `data/datasets/C6/**` contém cópias duplicadas, o texto deve dizer que a base rotulada partiu de 105 arquivos com deduplicação; se não, o número no código está errado.
- **Cap. 4 (extração):** "Docling ... PyPdfium acelerado por GPU CUDA": o `AcceleratorOptions(device="cuda")` acelera os modelos de layout do Docling; o backend PyPdfium é CPU. Reformular.
- **RAG como "pgvector":** `04_rag_pgvector.py:130` calcula as predições em memória (NumPy, cosseno, k = 3 com voto ponderado); o pgvector é usado só para medir a latência de 1,42 ms. A Tabela de hiperparâmetros omite k = 3 e o voto ponderado, e o texto fala em "vizinho" no singular.
- **Kafka:** `infra/docker-compose.yml` usa a imagem `dhi.io/kafka:4.3.0`; `docker-compose-externalinfra.yml` usa `apache/kafka:4.3.0`. O texto cita a segunda; deixar claro qual compose é o vigente.
- **Segredos e IPs fixos no código:** senha do PostgreSQL em `worker-prata/app.py:24` e `common.py:373-378`, chaves MinIO em `minioconfig.py` e `utils.py`, `appSecret`/`cookieSecret` do Logto em `web/src/logto.ts:3-6` (commitados), IP `192.168.15.18` espalhado. Contradiz a seção de segurança da informação financeira.

## 4. Lacunas de justificativa

- **Ancoramento em cascata para "Despesas Diversas / Outros" (1.8).** O texto atribui a concentração de erros nessa classe à "abstenção" do LLM sob a diretriz antialucinação. Dois mecanismos de código levam qualquer rótulo não reconhecido à mesma classe residual, sem que isso seja medido. A banca pode perguntar quantas das 111 transações absorvidas por "Despesas Diversas" foram produzidas pelo ancoramento e não pelo modelo. A coluna `categoria` bruta em `agente_teste_bruto.csv` permite essa contagem.
- **Degradação silenciosa de tool-calling:** `classificar_com_llm` (`nodes.py:155-158` e `183-185`) captura exceções e reexecuta sem ferramentas; `estruturar_saida_llm` pode fazer uma segunda chamada ao LLM. Isso afeta latência, determinismo e a interpretação do "não exercício" da ferramenta. Não há menção no texto.
- **`do_ocr = False` no worker:** decisão explícita de desligar o OCR no Docling, oposta ao que o texto descreve. Deve ser justificada (PDFs nativos, senha, custo) ou revertida.
- **Metadado de origem constante no teste cego (1.3):** a Q4 é respondida sem ter variado o único metadado injetado no prompt.
- **`MemorySaver` como checkpointer:** escolha que inviabiliza HITL assíncrono e multi-processo; o texto apresenta HITL como recurso de produção. Um `PostgresSaver` seria a decisão coerente com a arquitetura.
- **`usuario_id = 1` fixo em todos os parsers:** invalida "isolamento multi-inquilino" e a leitura do histórico "do usuário". Precisa ser declarado como limitação.
- **Semântica do consumidor Kafka:** `auto_offset_reset="latest"` com `enable_auto_commit=True`, uma partição, sem DLQ: entrega no máximo uma vez. O texto fala em "resiliência volumétrica"; a banca pode questionar perda de eventos em falha do worker.
- **Escolha do run sem ferramenta web (Seção 2):** existe um run com a ferramenta; a escolha de reportar o outro precisa ser justificada com os números do run descartado.
- **Reset da base vetorial na etapa 4:** contradiz o argumento de "cold start" e "aprendizado ativo" do Cap. 6 sem discussão.
- **Duas normalizações e três chaves de indexação (1.20):** ingestão, agente e base vetorial usam textos diferentes para o mesmo estabelecimento; o texto só reconhece a diferença consulta × indexação em nota de rodapé.
- **API de classificação com e5-large (1.14):** um segundo modelo de embeddings, de 1024 dimensões e zero-shot, presente no repositório e ausente da monografia.

## 5. Tabela de ação corretiva

| Ponto divergente / problema | Impacto | Correção sugerida |
|---|---|---|
| Run com DuckDuckGo existe (48 erros, acc 57,2 %), texto diz "não exercitado por falta de conectividade" | Alto | Ajustar o texto: relatar o run COMWEB, seus erros de backend e o motivo de adotar o SEMWEB |
| Histórico de marketplace nunca chega ao LLM; Mercado Livre nunca detectado (`mercado livre` × `mercado_livre`) | Alto | Ajustar o código (usar `detectar_marketplace`, injetar histórico no prompt, filtrar por estabelecimento) ou remover o nó do texto e da Q4 |
| HITL "aguarda usuário em produção" com `MemorySaver` e `confirmar_hitl=False` | Alto | Ajustar o texto (HITL simulado em ambos os modos) e, se possível, o código (`PostgresSaver` + endpoint de retomada) |
| Tesseract descrito como integrado à esteira; worker com `do_ocr=False` e sem pytesseract | Alto | Ajustar o texto: Tesseract usado só no benchmark; ou ligar `extrair_texto_avancado` como fallback no worker |
| Apêndice B apresenta `estabelecimentos` como base vetorial; agente consulta `langchain_pg_embedding` | Alto | Ajustar o texto (documentar as tabelas LangChain) e o índice/tipos do apêndice conforme `base.sql` |
| Ancoramento em cascata para "Despesas Diversas" não medido nem mencionado | Alto | Ajustar o texto e acrescentar contagem a partir de `agente_teste_bruto.csv` |
| Web descrita como painel orçamentário + HITL; é scaffold com upload simulado | Alto | Ajustar o texto (Apêndice C e Cap. 4) para o estado real do submódulo |
| `log_classificacoes` "registra todas as inferências"; nunca escrita | Alto | Ajustar o código (inserir em `salvar_resultado`) ou remover a afirmação do NFR e da seção LGPD |
| Logto/RBAC "protege as APIs"; APIs sem autenticação; `usuario_id=1` fixo | Alto | Ajustar o texto: Logto só na web, sem RBAC, single-tenant; registrar como limitação |
| Figura da arquitetura: Kafka → agente, worker → `bronze-txt` | Médio | Ajustar a figura para worker → PostgreSQL e agente em lote |
| PDF tratado como origem óptica; `source` fixo em CSV do C6 no teste cego | Médio | Ajustar o código (`.pdf` nativo na lista) e o texto da Q4 |
| Testes pytest descritos; `notebooks/tests` vazio | Médio | Ajustar o texto (retirar) ou criar testes mínimos para regex, parsers e Pydantic |
| Seed com 9 categorias em `base.sql`; solução exige 14 | Médio | Ajustar o código (script de seed das 14 categorias) e citar no Apêndice C |
| ByT5: MLflow registra `epochs=18, lr=3e-4`; real 12 e 5e-4 | Médio | Ajustar o código (`03_byt5.py:105`) e reexecutar o log |
| Autologging LangChain e `raciocinio.txt` só em notebook legado | Médio | Ajustar o texto (Cap. 4, MLflow) para o que `05_agente.py` registra |
| `service-classification` usa e5-large zero-shot | Médio | Ajustar o texto (declarar como protótipo não avaliado) ou alinhar a API ao agente |
| `estruturar_saida_llm`: regex antes de `with_structured_output`, segunda chamada ao LLM | Médio | Ajustar o texto (descrever a cascata real) |
| Duas normalizações e chave de `estabelecimentos` diferente | Médio | Ajustar o código (uma única `normalizar_nome` compartilhada) |
| `aimodules.py` com Claude via API em `worker-prata` | Médio | Remover o arquivo (código morto contradiz a tese de soberania) |
| Submódulo `web` sem `.gitmodules` | Médio | Ajustar o código (`git submodule add` com URL) |
| Latência "6,5 s por transação do ramo LLM" | Baixo | Ajustar o texto: 6,5 s é média global; ramo LLM ≈ 13,7 s |
| "≥ 0,85" no Cap. 5 vs "> 0,85" no Cap. 4 e código | Baixo | Ajustar o texto |
| Escopo cita OFX/JSON; ingestão aceita só CSV/PDF | Baixo | Ajustar o texto ou o `TipoArquivo` |
| Bucket `mlflow-artifacts` não criado; comandos soltos em `setup_minio.sh` | Baixo | Ajustar o código |
| Tabela de tecnologias: MinIO SDK vs AWS SDK; Python 3.11 vs cp312 | Baixo | Ajustar o texto |
| RAG: k=3 com voto ponderado e predição em NumPy | Baixo | Ajustar o texto (Tabela de hiperparâmetros) |
| Segredos e IPs fixos no código e `web/src/logto.ts` commitado | Baixo | Ajustar o código (variáveis de ambiente) e mencionar na seção de segurança |
| Benchmark OCR fora da esteira 01–10 | Baixo | Ajustar o texto do Apêndice C ou mover o notebook para uma etapa numerada |
