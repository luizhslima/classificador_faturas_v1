# statement-classifier

Extração e classificação automática de transações em faturas de cartão de crédito,
com preservação de leiaute e agentes de linguagem em infraestrutura local.

## Estrutura
- `service-ingestao/` — API de ingestão (Java/Spring WebFlux, Kafka, MinIO)
- `service-classification/` — API de classificação
- `worker-prata/` — worker de extração/OCR (camada prata)
- `infra/` — docker-compose e scripts (copie `infra/.env.example` para `infra/.env`)
- `notebooks/` — experimentos e módulos de apoio
- `specs/` — especificações e prompts

## Configuração
Copie `.env.example` para `.env` e preencha os valores. Nenhum dado real de faturas
é versionado: coloque os dados em `data/` (ignorado pelo git).
