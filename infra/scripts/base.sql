-- =============================================
-- BASE DE CONHECIMENTO: CLASSIFICADOR DE FATURA
-- Requer extensão pgvector instalada
-- =============================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm; -- para busca fuzzy por texto

-- =============================================
-- CATEGORIAS E SUBCATEGORIAS
-- =============================================

CREATE TABLE categorias (
    id          SERIAL PRIMARY KEY,
    nome        TEXT NOT NULL UNIQUE,
    descricao   TEXT,
    icone       TEXT,
    ativo       BOOLEAN DEFAULT TRUE,
    criado_em   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE subcategorias (
    id           SERIAL PRIMARY KEY,
    categoria_id INTEGER NOT NULL REFERENCES categorias(id) ON DELETE CASCADE,
    nome         TEXT NOT NULL,
    descricao    TEXT,
    ativo        BOOLEAN DEFAULT TRUE,
    criado_em    TIMESTAMP DEFAULT NOW(),
    UNIQUE (categoria_id, nome)
);

-- =============================================
-- BASE DE CONHECIMENTO DE ESTABELECIMENTOS
-- Coração do sistema RAG
-- =============================================

CREATE TABLE estabelecimentos (
    id                  SERIAL PRIMARY KEY,
    nome_original       TEXT NOT NULL,
    nome_normalizado    TEXT NOT NULL,
    categoria_id        INTEGER REFERENCES categorias(id),
    subcategoria_id     INTEGER REFERENCES subcategorias(id),
    confianca           REAL DEFAULT 0.0 CHECK (confianca BETWEEN 0 AND 1),
    fonte               TEXT,                          -- 'llm', 'manual', 'usuario', 'importacao'
    metadados           JSONB DEFAULT '{}',            -- site, cidade, pais, tipo, tags, etc.
    embedding           VECTOR(384),                   -- embedding semântico do nome normalizado
    qtd_transacoes      INTEGER DEFAULT 1,
    ultima_atualizacao  TIMESTAMP DEFAULT NOW(),
    criado_em           TIMESTAMP DEFAULT NOW()
);

-- Índices para busca eficiente
CREATE INDEX idx_estab_nome_normalizado   ON estabelecimentos(nome_normalizado);
CREATE INDEX idx_estab_categoria          ON estabelecimentos(categoria_id);
CREATE INDEX idx_estab_confianca          ON estabelecimentos(confianca);
CREATE INDEX idx_estab_nome_trgm          ON estabelecimentos USING GIN (nome_normalizado gin_trgm_ops);
CREATE INDEX idx_estab_embedding_hnsw     ON estabelecimentos USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- =============================================
-- USUÁRIOS
-- =============================================

CREATE TABLE usuarios (
    id          SERIAL PRIMARY KEY,
    nome        TEXT NOT NULL,
    email       TEXT UNIQUE NOT NULL,
    ativo       BOOLEAN DEFAULT TRUE,
    criado_em   TIMESTAMP DEFAULT NOW()
);

-- =============================================
-- FATURAS
-- =============================================

CREATE TABLE faturas (
    id              SERIAL PRIMARY KEY,
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    referencia      TEXT,                   -- ex: '2025-06', 'Junho/2025'
    data_inicio     DATE,
    data_fim        DATE,
    valor_total     NUMERIC(12, 2),
    arquivo_origem  TEXT,                   -- nome/path do arquivo importado
    status          TEXT DEFAULT 'pendente', -- 'pendente', 'processando', 'concluida', 'erro'
    criado_em       TIMESTAMP DEFAULT NOW()
);

-- =============================================
-- TRANSAÇÕES
-- =============================================

CREATE TABLE transacoes (
    id                  SERIAL PRIMARY KEY,
    fatura_id           INTEGER NOT NULL REFERENCES faturas(id) ON DELETE CASCADE,
    nome_original       TEXT NOT NULL,          -- texto bruto da fatura (ex: "PAG*ABC123")
    nome_normalizado    TEXT,                   -- após limpeza/normalização
    valor               NUMERIC(12, 2) NOT NULL,
    data_transacao      DATE NOT NULL,
    categoria_id        INTEGER REFERENCES categorias(id),
    subcategoria_id     INTEGER REFERENCES subcategorias(id),
    estabelecimento_id  INTEGER REFERENCES estabelecimentos(id),
    confianca           REAL CHECK (confianca BETWEEN 0 AND 1),
    metodo_classificacao TEXT,                  -- 'cache', 'vetorial', 'llm', 'manual'
    revisado_usuario    BOOLEAN DEFAULT FALSE,
    criado_em           TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_transacoes_fatura       ON transacoes(fatura_id);
CREATE INDEX idx_transacoes_categoria    ON transacoes(categoria_id);
CREATE INDEX idx_transacoes_data         ON transacoes(data_transacao);
CREATE INDEX idx_transacoes_metodo       ON transacoes(metodo_classificacao);

-- =============================================
-- LOG DE CLASSIFICAÇÕES (rastreabilidade)
-- =============================================

CREATE TABLE log_classificacoes (
    id                  SERIAL PRIMARY KEY,
    transacao_id        INTEGER NOT NULL REFERENCES transacoes(id) ON DELETE CASCADE,
    nome_entrada        TEXT NOT NULL,
    categoria_sugerida  TEXT,
    subcategoria_sugerida TEXT,
    confianca           REAL,
    metodo              TEXT,               -- 'cache', 'vetorial', 'llm'
    prompt_usado        TEXT,               -- prompt enviado ao LLM (se aplicável)
    resposta_llm        TEXT,               -- resposta bruta do LLM (se aplicável)
    similaridade        REAL,               -- score da busca vetorial (se aplicável)
    tempo_ms            INTEGER,            -- tempo de processamento em ms
    criado_em           TIMESTAMP DEFAULT NOW()
);

-- =============================================
-- FEEDBACK DO USUÁRIO (aprendizado contínuo)
-- =============================================

CREATE TABLE feedbacks (
    id                      SERIAL PRIMARY KEY,
    transacao_id            INTEGER NOT NULL REFERENCES transacoes(id) ON DELETE CASCADE,
    usuario_id              INTEGER REFERENCES usuarios(id),
    categoria_original_id   INTEGER REFERENCES categorias(id),
    categoria_corrigida_id  INTEGER NOT NULL REFERENCES categorias(id),
    subcategoria_corrigida_id INTEGER REFERENCES subcategorias(id),
    observacao              TEXT,
    criado_em               TIMESTAMP DEFAULT NOW()
);

-- =============================================
-- SEED: CATEGORIAS PADRÃO
-- =============================================

INSERT INTO categorias (nome, descricao) VALUES
    ('Alimentação',  'Restaurantes, delivery, mercados'),
    ('Transporte',   'Combustível, transporte público, aplicativos'),
    ('Compras',      'Lojas, e-commerce, marketplace'),
    ('Saúde',        'Farmácias, clínicas, planos de saúde'),
    ('Lazer',        'Entretenimento, viagens, hobbies'),
    ('Streaming',    'Serviços de assinatura de mídia'),
    ('Educação',     'Cursos, livros, plataformas educacionais'),
    ('Serviços',     'Contas, assinaturas e serviços gerais'),
    ('Outros',       'Não classificado ou categoria genérica');

INSERT INTO subcategorias (categoria_id, nome) VALUES
    (1, 'Restaurante'),
    (1, 'Delivery'),
    (1, 'Supermercado'),
    (2, 'Combustível'),
    (2, 'Aplicativo de transporte'),
    (2, 'Estacionamento'),
    (3, 'Marketplace'),
    (3, 'Loja física'),
    (6, 'Vídeo'),
    (6, 'Música'),
    (6, 'Games');