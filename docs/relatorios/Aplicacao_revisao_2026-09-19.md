# Aplicação da revisão de 19/09/2026 (relatório "TCC Luiz Henrique Lima 2026-09-19 Revisão Claude")

Aplicado em 20/09/2026. Compilação: 147 páginas, sem erros, sem referências ou citações indefinidas.

## Moderados (12/12)

| Achado | Ação |
|---|---|
| Métricas de classificação sem citação (2.2.5) | Sokolova e Lapalme (2009) citados na definição e na agregação macro/ponderada |
| LLMs sem referência-base; Pydantic sem fonte (2.4.2) | Brown et al. (2020) e documentação do Pydantic (2025) adicionados ao `.bib` |
| Resultados quantitativos ausentes em 3.6.1, 3.6.2, 3.6.3, 3.6.5 | Números extraídos dos próprios trabalhos: Zhang et al. (Tabela 4), Dhingra et al. (Tabela 3), Huang et al. (SROIE: 16/7/1 equipes acima de 90%, 90,49% na Tarefa 3), Santos (85,35% SVM vs 69,04% tweet2vec), Souza (97,3% de acurácia, 35,3 s/documento). **Correção substantiva:** a monografia afirmava que, em Santos (2022), o modelo por caracteres superou a linha de base clássica; o resultado é o inverso (TF-IDF + SVM linear venceu), e passa a ser citado como precedente nacional do achado central |
| Hipótese nula não enunciada (4.2) | Pares H0/H1 para H1a e H1b, α = 0,05 e critério de decisão enunciados na Seção 4.2 |
| Configuração do LM Studio não registrada (5.2) | Documentada retroativamente a partir do log do servidor de 08/09/2026: gemma-4-E4B-it, GGUF Q4_K_M, llama.cpp CUDA 12 (2.33.0), contexto 8.192 tokens, 4 slots, temperature 0 e max_completion_tokens 2048 enviados em todas as 509 requisições; top-p/top-k/semente = 40, 0,95 e semente aleatória (-1), informados pelo autor; sem efeito sob temperatura 0 |
| CER "abaixo de 2,5% em 2024–2026" contrariado pela Tabela 6 | Reformulado: abaixo de 5% a partir de 2024 e abaixo de 2,5% em 2025–2026 |
| Figura 4 fora de ordem cronológica | Figuras 3–9 regeneradas por `notebooks/experimentos/12_figuras.py` (eixo ordenado, sem títulos internos, rótulos iguais aos das tabelas, fontes maiores, Figura 5 empilhada, "Limiar da hipótese (85%)", "Híbrido" acentuado, n por categoria na Figura 8) |
| Legenda "Meta TCC (85%)" na Figura 6 | Idem; também corrigido em `06_consolidar.py` |
| Remissões trocadas na Seção 6.5 | Item 4 → limitação 14; item 5 → limitações 3, 4, 7 e 13 |
| Chamadas institucionais inconsistentes | Citações manuais "(Poder360, 2025)", "(SPC Brasil, 2024)", "(Brasil, 2018)" convertidas em `\cite`; autores institucionais mantidos em caixa alta no `.bib` (norma para citação entre parênteses e lista); CGU movida do campo autor para o título em `brasilcpgf` |
| Itálico de estrangeirismos inconsistente | Varredura automática (`marketplace`, `embedding`, `e-commerce`, `lakehouse`, `dataset`, `backend`, `wrapper`, `checkpointer`, `fallback`, `clusters`); convenção "lakehouse" em minúsculas e itálico; títulos 2.5.1, 2.5.2, 2.5.3 e 4.5 ajustados; nota declarando que rótulos de categoria ficam em redondo (5.3) |
| Revisão sistemática (questão de avaliação) | Sem ação: o texto já declara tratar-se de levantamento estruturado |

## Leves (36): 26 aplicados, 4 parciais, 6 não aplicados

**Aplicados:** capitalização dos títulos 2.5.1, 2.5.2, 2.5.3 e 4.5; Seção 6.6 fundida ao fecho de 6.3 (6.1 mantida); folha de rosto; palavras-chave dos metadados do PDF; organização da monografia em parágrafo corrido; antecipação do roteiro removida do primeiro parágrafo; *clusters* em itálico; DLA ancorada em Binmakhashen e Mahmoud (2019); word2vec (Mikolov et al., 2013); amostragem por incerteza (Lewis e Gale, 1994); 2.2.1 condensada; *drift* declarado como motivador já em 2.5.1; SROIE padronizado como Huang et al. (2019); janela temporal harmonizada (Cap. 3 e Apêndice A); nomenclatura "PostgreSQL + pgvector"/"pgvector" nas figuras; rótulos da Figura 6 iguais aos da Tabela 7 e "Híbrido" acentuado; títulos internos removidos das Figuras 3–6; fontes ampliadas nas Figuras 4 e 5 (Figura 5 empilhada); nota conciliando as contagens LLM/humano em 5.6.2; justificativa do recorte de 14 faturas; conclusões amarradas a Q1–Q5; sobreposição 6.2/6.3/6.6 eliminada; título de Gil (2019) e de Caseli e Nunes (2024) em caixa baixa; estrangeirismos nunca italicizados (*score* → escore, *dataset*, *backend*, *wrapper*, *checkpointer*, *fallback*); oscilação de maiúsculas resolvida (convenção *lakehouse*; Bronze/Silver/Gold já eram uniformes); ortografia e numeração corrigidas no código-fonte; períodos longos segmentados (4.5, 5.6.2, 5.6.3).

**Parciais:** compactação da motivação/objetivos do Cap. 1 (lista de organização convertida e antecipação removida; enumeração dos cinco obstáculos mantida por ser substantiva); 3.6.1 (mantida a fusão, com "Validação e Resultados" separados por autor, opção admitida pelo revisor); repetição do achado de 23–25 p.p. (reduzida a remissão em 6.2; mantida no Resumo, em 5.6, na Tabela 9, em 5.8 e na conclusão 2, onde é o conteúdo); repetição das ressalvas do ramo LLM (5.6.5 e 5.8 remetem a 5.2; a conclusão 4 conserva os quatro fatores por ser a conclusão).

**Aplicado em 21/09:** data de acesso acrescentada às 42 entradas com DOI (datas entre 08 e 20 set. 2026, a pedido do autor).

**Não aplicados:** recomendação opcional de evolução para RSL (sem ação por natureza); `.gitmodules` do submódulo `web` (a aplicação não tem repositório remoto; Apêndice C passou a declarar isso); credenciais em claro (alteração de código fora desta rodada); localizador eletrônico nas 5 entradas sem DOI; período final do Resumo (substituído integralmente pela versão proposta).

## Resumo e Abstract

Substituídos pela versão proposta no relatório (objetivo enunciado como tal, período de classificação depurado, resultado marginal do Naive Bayes retirado do Resumo, "dois conjuntos de dados reais"), com as palavras-chave mantidas.

## Não aplicados (e por quê)

- **Data de acesso nas referências com DOI** e **localizador nas entradas sem DOI**: item agrupado de menor prioridade; exigiria conferir cerca de 40 entradas uma a uma.
- **`.gitmodules` do submódulo `web`**: o submódulo local não tem remoto configurado; a URL de publicação precisa ser informada pelo autor.
- **Credenciais em claro**: correção de código fora do escopo desta rodada de texto; permanece registrada como pendência na Seção 4.8 e no Apêndice C.
- **Compactação da motivação/objetivos do Cap. 1** além do já feito: mantida a enumeração dos cinco obstáculos por ser substantiva.
