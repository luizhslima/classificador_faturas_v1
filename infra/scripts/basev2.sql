-- ==========================================================
-- ATUALIZAÇÃO DA BASE PARA MARKETPLACES E MULTICATEGORIAS
-- PostgreSQL + pgvector
-- ==========================================================

-- ----------------------------------------------------------
-- 1. CLASSIFICA O TIPO DE ESTABELECIMENTO
-- ----------------------------------------------------------
-- Exemplos:
-- restaurante, farmacia, posto_combustivel, streaming,
-- marketplace, loja_departamento, servico, desconhecido.

CREATE TABLE tipos_estabelecimento (
    id          SERIAL PRIMARY KEY,
    nome        TEXT NOT NULL UNIQUE,
    descricao   TEXT,
    criado_em   TIMESTAMP NOT NULL DEFAULT NOW()
);

INSERT INTO tipos_estabelecimento (nome, descricao)
VALUES
    ('restaurante', 'Estabelecimento de alimentação pronta'),
    ('supermercado', 'Mercado, atacado ou mercearia'),
    ('farmacia', 'Farmácia ou drogaria'),
    ('posto_combustivel', 'Posto de combustível'),
    ('streaming', 'Assinatura de vídeo, música ou entretenimento'),
    ('marketplace', 'Plataforma com múltiplos vendedores e categorias'),
    ('loja_departamento', 'Loja com múltiplos tipos de produto'),
    ('servico', 'Prestador de serviço'),
    ('desconhecido', 'Tipo ainda não identificado')
ON CONFLICT (nome) DO NOTHING;

ALTER TABLE estabelecimentos
    ADD COLUMN IF NOT EXISTS tipo_estabelecimento_id
        INTEGER REFERENCES tipos_estabelecimento(id);

ALTER TABLE estabelecimentos
    ADD COLUMN IF NOT EXISTS eh_marketplace BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_estabelecimentos_tipo
    ON estabelecimentos(tipo_estabelecimento_id);

CREATE INDEX IF NOT EXISTS idx_estabelecimentos_marketplace
    ON estabelecimentos(eh_marketplace)
    WHERE eh_marketplace = TRUE;

-- Marca marketplaces conhecidos.
-- Ajuste os nomes de acordo com os estabelecimentos da sua base.
UPDATE estabelecimentos
SET
    eh_marketplace = TRUE,
    tipo_estabelecimento_id = (
        SELECT id
        FROM tipos_estabelecimento
        WHERE nome = 'marketplace'
    ),
    categoria_id = NULL,
    subcategoria_id = NULL
WHERE nome_normalizado IN (
    'mercado livre',
    'mercado pago',
    'amazon',
    'shopee',
    'magalu',
    'magazine luiza',
    'americanas',
    'aliexpress',
    'shein'
);

-- ----------------------------------------------------------
-- 2. ADICIONA "MARKETPLACE" COMO CATEGORIA PRINCIPAL
-- ----------------------------------------------------------
-- Essa categoria representa o canal de compra, não o item comprado.

INSERT INTO categorias (nome, descricao)
VALUES (
    'Marketplace',
    'Compra realizada em plataforma com múltiplos vendedores e categorias'
)
ON CONFLICT (nome) DO NOTHING;

-- ----------------------------------------------------------
-- 3. TABELA DE SUGESTÕES DE CATEGORIA POR USUÁRIO
-- ----------------------------------------------------------
-- NÃO é uma classificação definitiva.
-- Exemplo:
-- usuário 10 + Mercado Livre:
-- Eletrônicos: 18 confirmações
-- Casa: 5 confirmações
-- Alimentação: 2 confirmações

CREATE TABLE sugestoes_categoria_marketplace (
    id                  BIGSERIAL PRIMARY KEY,
    usuario_id          INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    estabelecimento_id  INTEGER NOT NULL REFERENCES estabelecimentos(id) ON DELETE CASCADE,
    categoria_id        INTEGER NOT NULL REFERENCES categorias(id),
    subcategoria_id     INTEGER REFERENCES subcategorias(id),

    quantidade_confirmada INTEGER NOT NULL DEFAULT 0
        CHECK (quantidade_confirmada >= 0),

    quantidade_sugerida INTEGER NOT NULL DEFAULT 0
        CHECK (quantidade_sugerida >= 0),

    confianca_historica REAL NOT NULL DEFAULT 0.0
        CHECK (confianca_historica BETWEEN 0 AND 1),

    primeira_ocorrencia TIMESTAMP,
    ultima_ocorrencia   TIMESTAMP,
    atualizado_em       TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE (
        usuario_id,
        estabelecimento_id,
        categoria_id,
        subcategoria_id
    )
);

CREATE INDEX idx_sugestao_marketplace_usuario_estabelecimento
    ON sugestoes_categoria_marketplace(usuario_id, estabelecimento_id);

CREATE INDEX idx_sugestao_marketplace_confianca
    ON sugestoes_categoria_marketplace(confianca_historica DESC);

-- ----------------------------------------------------------
-- 4. CAMPOS DE CLASSIFICAÇÃO ESPECÍFICOS NA TRANSAÇÃO
-- ----------------------------------------------------------
-- A transação mantém "Marketplace" como categoria principal,
-- podendo ter uma sugestão de categoria de item.

ALTER TABLE transacoes
    ADD COLUMN IF NOT EXISTS categoria_sugerida_id
        INTEGER REFERENCES categorias(id);

ALTER TABLE transacoes
    ADD COLUMN IF NOT EXISTS subcategoria_sugerida_id
        INTEGER REFERENCES subcategorias(id);

ALTER TABLE transacoes
    ADD COLUMN IF NOT EXISTS confianca_sugestao REAL
        CHECK (confianca_sugestao BETWEEN 0 AND 1);

ALTER TABLE transacoes
    ADD COLUMN IF NOT EXISTS requer_confirmacao BOOLEAN
        NOT NULL DEFAULT FALSE;

ALTER TABLE transacoes
    ADD COLUMN IF NOT EXISTS status_classificacao TEXT
        NOT NULL DEFAULT 'pendente'
        CHECK (
            status_classificacao IN (
                'pendente',
                'classificada',
                'sugerida',
                'confirmada_usuario',
                'rejeitada_usuario',
                'sem_evidencia'
            )
        );

ALTER TABLE transacoes
    ADD COLUMN IF NOT EXISTS origem_detalhamento TEXT
        CHECK (
            origem_detalhamento IS NULL OR
            origem_detalhamento IN (
                'fatura',
                'historico_usuario',
                'nota_fiscal',
                'email',
                'api_marketplace',
                'usuario',
                'estimativa'
            )
        );

CREATE INDEX idx_transacoes_requer_confirmacao
    ON transacoes(requer_confirmacao)
    WHERE requer_confirmacao = TRUE;

CREATE INDEX idx_transacoes_categoria_sugerida
    ON transacoes(categoria_sugerida_id);

CREATE INDEX idx_transacoes_status_classificacao
    ON transacoes(status_classificacao);

-- ----------------------------------------------------------
-- 5. ALOCAÇÕES DE CATEGORIA POR TRANSAÇÃO
-- ----------------------------------------------------------
-- Permite uma compra possuir diversas categorias.
--
-- Exemplo:
-- Mercado Livre: R$ 235,90
-- Alimentação: R$ 35,90
-- Eletrônicos:  R$ 200,00

CREATE TABLE transacao_alocacoes_categoria (
    id                  BIGSERIAL PRIMARY KEY,
    transacao_id        INTEGER NOT NULL REFERENCES transacoes(id) ON DELETE CASCADE,
    categoria_id        INTEGER NOT NULL REFERENCES categorias(id),
    subcategoria_id     INTEGER REFERENCES subcategorias(id),

    valor_alocado       NUMERIC(12, 2) NOT NULL CHECK (valor_alocado >= 0),
    percentual_alocado  NUMERIC(7, 4)
        CHECK (percentual_alocado >= 0 AND percentual_alocado <= 100),

    confianca           REAL NOT NULL DEFAULT 1.0
        CHECK (confianca BETWEEN 0 AND 1),

    fonte               TEXT NOT NULL
        CHECK (
            fonte IN (
                'usuario',
                'nota_fiscal',
                'email',
                'api_marketplace',
                'historico_usuario',
                'llm',
                'estimativa'
            )
        ),

    confirmado          BOOLEAN NOT NULL DEFAULT FALSE,
    observacao          TEXT,
    criado_em           TIMESTAMP NOT NULL DEFAULT NOW(),
    atualizado_em       TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE (
        transacao_id,
        categoria_id,
        subcategoria_id
    )
);

CREATE INDEX idx_alocacoes_transacao
    ON transacao_alocacoes_categoria(transacao_id);

CREATE INDEX idx_alocacoes_categoria
    ON transacao_alocacoes_categoria(categoria_id);

CREATE INDEX idx_alocacoes_confirmadas
    ON transacao_alocacoes_categoria(confirmado)
    WHERE confirmado = TRUE;

-- ----------------------------------------------------------
-- 6. RESTRIÇÃO: SOMA DAS ALOCAÇÕES NÃO PODE EXCEDER A COMPRA
-- ----------------------------------------------------------

CREATE OR REPLACE FUNCTION validar_total_alocado_transacao()
RETURNS TRIGGER AS $$
DECLARE
    total_alocado NUMERIC(12, 2);
    valor_transacao NUMERIC(12, 2);
    id_transacao INTEGER;
BEGIN
    id_transacao := COALESCE(NEW.transacao_id, OLD.transacao_id);

    SELECT valor
    INTO valor_transacao
    FROM transacoes
    WHERE id = id_transacao;

    SELECT COALESCE(SUM(valor_alocado), 0)
    INTO total_alocado
    FROM transacao_alocacoes_categoria
    WHERE transacao_id = id_transacao;

    IF total_alocado > valor_transacao THEN
        RAISE EXCEPTION
            'O total das alocações (R$ %) excede o valor da transação (R$ %).',
            total_alocado,
            valor_transacao;
    END IF;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validar_total_alocado
    ON transacao_alocacoes_categoria;

CREATE TRIGGER trg_validar_total_alocado
AFTER INSERT OR UPDATE OR DELETE
ON transacao_alocacoes_categoria
FOR EACH ROW
EXECUTE FUNCTION validar_total_alocado_transacao();

-- ----------------------------------------------------------
-- 7. HISTÓRICO DE CONFIRMAÇÕES POR USUÁRIO
-- ----------------------------------------------------------
-- Registra cada ação do usuário, útil para auditoria e
-- posterior atualização das sugestões agregadas.

CREATE TABLE confirmacoes_categoria_marketplace (
    id                  BIGSERIAL PRIMARY KEY,
    usuario_id          INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    transacao_id        INTEGER NOT NULL REFERENCES transacoes(id) ON DELETE CASCADE,
    estabelecimento_id  INTEGER NOT NULL REFERENCES estabelecimentos(id),
    categoria_id        INTEGER NOT NULL REFERENCES categorias(id),
    subcategoria_id     INTEGER REFERENCES subcategorias(id),

    valor_confirmado    NUMERIC(12, 2),
    confirmado_em       TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE (
        usuario_id,
        transacao_id,
        categoria_id,
        subcategoria_id
    )
);

CREATE INDEX idx_confirmacao_marketplace_usuario_estabelecimento
    ON confirmacoes_categoria_marketplace(usuario_id, estabelecimento_id);

-- ----------------------------------------------------------
-- 8. VIEW PARA CONSULTAR O PERFIL DE COMPRA DO USUÁRIO
-- ----------------------------------------------------------

CREATE OR REPLACE VIEW vw_perfil_categoria_marketplace AS
SELECT
    scm.usuario_id,
    scm.estabelecimento_id,
    e.nome_normalizado AS marketplace,
    c.nome AS categoria,
    sc.nome AS subcategoria,
    scm.quantidade_confirmada,
    scm.quantidade_sugerida,
    scm.confianca_historica,
    scm.ultima_ocorrencia
FROM sugestoes_categoria_marketplace scm
INNER JOIN estabelecimentos e
    ON e.id = scm.estabelecimento_id
INNER JOIN categorias c
    ON c.id = scm.categoria_id
LEFT JOIN subcategorias sc
    ON sc.id = scm.subcategoria_id;



ALTER TABLE estabelecimentos
ADD COLUMN IF NOT EXISTS eh_marketplace BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS estabelecimento_aliases (
    id BIGSERIAL PRIMARY KEY,

    estabelecimento_id INTEGER NOT NULL
        REFERENCES estabelecimentos(id)
        ON DELETE CASCADE,

    alias_normalizado TEXT NOT NULL,
    tipo_match TEXT NOT NULL DEFAULT 'exato',
    prioridade SMALLINT NOT NULL DEFAULT 100,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,

    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_estabelecimento_alias
        UNIQUE (estabelecimento_id, alias_normalizado),

    CONSTRAINT ck_tipo_match
        CHECK (tipo_match IN ('exato', 'prefixo', 'contem'))
);

CREATE INDEX IF NOT EXISTS ix_estabelecimento_aliases_exato
    ON estabelecimento_aliases (alias_normalizado)
    WHERE ativo = TRUE;

CREATE INDEX IF NOT EXISTS ix_estabelecimento_aliases_tipo_prioridade
    ON estabelecimento_aliases (tipo_match, prioridade)
    WHERE ativo = TRUE;


ALTER TABLE faturas ADD COLUMN IF NOT EXISTS uuid_fatura UUID UNIQUE;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_faturas_arquivo_origem'
          AND conrelid = 'faturas'::regclass
    ) THEN
        ALTER TABLE faturas
        ADD CONSTRAINT uq_faturas_arquivo_origem
        UNIQUE (arquivo_origem);
    END IF;
END $$;