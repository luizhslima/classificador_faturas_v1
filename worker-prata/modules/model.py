from __future__ import annotations

import uuid

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ----
# CATEGORIAS
# ----

class Categoria(Base):
    __tablename__ = "categorias"

    id:        Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome:      Mapped[str]            = mapped_column(Text, nullable=False, unique=True)
    descricao: Mapped[Optional[str]]  = mapped_column(Text)
    icone:     Mapped[Optional[str]]  = mapped_column(Text)
    ativo:     Mapped[bool]           = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[Optional[datetime]] = mapped_column(server_default=func.now())

    subcategorias: Mapped[list["Subcategoria"]] = relationship(
        "Subcategoria", back_populates="categoria"
    )
    transacoes: Mapped[list["Transacao"]] = relationship(
        "Transacao", foreign_keys="Transacao.categoria_id", back_populates="categoria"
    )


class Subcategoria(Base):
    __tablename__ = "subcategorias"
    __table_args__ = (
        UniqueConstraint("categoria_id", "nome"),
    )

    id:           Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    categoria_id: Mapped[int]           = mapped_column(ForeignKey("categorias.id", ondelete="CASCADE"), nullable=False)
    nome:         Mapped[str]           = mapped_column(Text, nullable=False)
    descricao:    Mapped[Optional[str]] = mapped_column(Text)
    ativo:        Mapped[bool]          = mapped_column(Boolean, nullable=False, default=True)
    criado_em:    Mapped[Optional[datetime]] = mapped_column(server_default=func.now())

    categoria: Mapped["Categoria"] = relationship("Categoria", back_populates="subcategorias")


# ----
# TIPOS DE ESTABELECIMENTO
# ----

class TipoEstabelecimento(Base):
    __tablename__ = "tipos_estabelecimento"

    id:        Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome:      Mapped[str]            = mapped_column(Text, nullable=False, unique=True)
    descricao: Mapped[Optional[str]]  = mapped_column(Text)
    criado_em: Mapped[datetime]       = mapped_column(nullable=False, server_default=func.now())

    estabelecimentos: Mapped[list["Estabelecimento"]] = relationship(
        "Estabelecimento", back_populates="tipo_estabelecimento"
    )


# ----
# ESTABELECIMENTOS (base de conhecimento RAG)
# ----

class Estabelecimento(Base):
    __tablename__ = "estabelecimentos"

    id:                   Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome_original:        Mapped[str]            = mapped_column(Text, nullable=False)
    nome_normalizado:     Mapped[str]            = mapped_column(Text, nullable=False)
    categoria_id:         Mapped[Optional[int]]  = mapped_column(ForeignKey("categorias.id"))
    subcategoria_id:      Mapped[Optional[int]]  = mapped_column(ForeignKey("subcategorias.id"))
    tipo_estabelecimento_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tipos_estabelecimento.id"))
    eh_marketplace:       Mapped[bool]           = mapped_column(Boolean, nullable=False, default=False)
    confianca:            Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3), default=0.0)
    fonte:                Mapped[Optional[str]]  = mapped_column(Text)  # 'llm', 'manual', 'usuario', 'importacao'
    metadados:            Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)  # site, cidade, pais, tipo, tags, etc.
    embedding:            Mapped[Optional[list]] = mapped_column(Vector(384))
    qtd_transacoes:       Mapped[Optional[int]]  = mapped_column(Integer, default=1)
    ultima_atualizacao:   Mapped[Optional[datetime]] = mapped_column(server_default=func.now())
    criado_em:            Mapped[Optional[datetime]] = mapped_column(server_default=func.now())

    categoria:             Mapped[Optional["Categoria"]]          = relationship("Categoria")
    subcategoria:          Mapped[Optional["Subcategoria"]]        = relationship("Subcategoria")
    tipo_estabelecimento:  Mapped[Optional["TipoEstabelecimento"]] = relationship(
        "TipoEstabelecimento", back_populates="estabelecimentos"
    )
    transacoes:            Mapped[list["Transacao"]]               = relationship(
        "Transacao", back_populates="estabelecimento"
    )
    sugestoes_marketplace: Mapped[list["SugestaoCategoriaMarketplace"]] = relationship(
        "SugestaoCategoriaMarketplace", back_populates="estabelecimento"
    )
    aliases:               Mapped[list["EstabelecimentoAlias"]]    = relationship(
        "EstabelecimentoAlias", back_populates="estabelecimento", cascade="all, delete-orphan"
    )


# ----
# USUÁRIOS
# ----

class Usuario(Base):
    __tablename__ = "usuarios"

    id:        Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome:      Mapped[str]            = mapped_column(Text, nullable=False)
    email:     Mapped[str]            = mapped_column(Text, nullable=False, unique=True)
    ativo:     Mapped[bool]           = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[Optional[datetime]] = mapped_column(server_default=func.now())

    faturas:               Mapped[list["Fatura"]]                          = relationship("Fatura", back_populates="usuario")
    sugestoes_marketplace: Mapped[list["SugestaoCategoriaMarketplace"]]    = relationship(
        "SugestaoCategoriaMarketplace", back_populates="usuario"
    )
    confirmacoes:          Mapped[list["ConfirmacaoCategoriaMarketplace"]] = relationship(
        "ConfirmacaoCategoriaMarketplace", back_populates="usuario"
    )


# ----
# FATURAS
# ----

class Fatura(Base):
    __tablename__ = "faturas"

    id:             Mapped[int]             = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id:     Mapped[int]             = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    referencia:     Mapped[Optional[str]]   = mapped_column(Text)           # ex: '2025-06'
    data_inicio:    Mapped[Optional[date]]  = mapped_column(Date)
    data_fim:       Mapped[Optional[date]]  = mapped_column(Date)
    valor_total:    Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    arquivo_origem: Mapped[Optional[str]]   = mapped_column(Text)
    status:         Mapped[Optional[str]]   = mapped_column(Text, default="pendente")  # 'pendente', 'processando', 'concluida', 'erro'
    criado_em:      Mapped[Optional[datetime]] = mapped_column(server_default=func.now())
    uuid_fatura:    Mapped[uuid.UUID] = mapped_column(unique=True, nullable=False)
    usuario:    Mapped["Usuario"]        = relationship("Usuario", back_populates="faturas")
    transacoes: Mapped[list["Transacao"]] = relationship("Transacao", back_populates="fatura")


# ----
# TRANSAÇÕES
# ----

class Transacao(Base):
    __tablename__ = "transacoes"
    __table_args__ = (
        CheckConstraint("confianca BETWEEN 0 AND 1"),
        CheckConstraint("confianca_sugestao BETWEEN 0 AND 1"),
        CheckConstraint(
            "status_classificacao IN ("
            "'pendente','classificada','sugerida',"
            "'confirmada_usuario','rejeitada_usuario','sem_evidencia')"
        ),
        CheckConstraint(
            "origem_detalhamento IS NULL OR origem_detalhamento IN ("
            "'fatura','historico_usuario','nota_fiscal',"
            "'email','api_marketplace','usuario','estimativa')"
        ),
    )

    id:                      Mapped[int]             = mapped_column(Integer, primary_key=True, autoincrement=True)
    fatura_id:               Mapped[int]             = mapped_column(ForeignKey("faturas.id", ondelete="CASCADE"), nullable=False)
    nome_original:           Mapped[str]             = mapped_column(Text, nullable=False)
    nome_normalizado:        Mapped[Optional[str]]   = mapped_column(Text)
    valor:                   Mapped[Decimal]         = mapped_column(Numeric(12, 2), nullable=False)
    data_transacao:          Mapped[date]            = mapped_column(Date, nullable=False)

    # classificação principal
    categoria_id:            Mapped[Optional[int]]   = mapped_column(ForeignKey("categorias.id"))
    subcategoria_id:         Mapped[Optional[int]]   = mapped_column(ForeignKey("subcategorias.id"))
    estabelecimento_id:      Mapped[Optional[int]]   = mapped_column(ForeignKey("estabelecimentos.id"))
    confianca:               Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))
    metodo_classificacao:    Mapped[Optional[str]]   = mapped_column(Text)  # 'cache', 'vetorial', 'llm', 'manual'

    # sugestão de item (marketplace)
    categoria_sugerida_id:    Mapped[Optional[int]]  = mapped_column(ForeignKey("categorias.id"))
    subcategoria_sugerida_id: Mapped[Optional[int]]  = mapped_column(ForeignKey("subcategorias.id"))
    confianca_sugestao:       Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))
    origem_detalhamento:      Mapped[Optional[str]]  = mapped_column(Text)

    # controle de fluxo
    requer_confirmacao:   Mapped[bool]            = mapped_column(Boolean, nullable=False, default=False)
    status_classificacao: Mapped[str]             = mapped_column(Text, nullable=False, default="pendente")
    revisado_usuario:     Mapped[Optional[bool]]  = mapped_column(Boolean, default=False)
    criado_em:            Mapped[Optional[datetime]] = mapped_column(server_default=func.now())

    fatura:               Mapped["Fatura"]                              = relationship("Fatura", back_populates="transacoes")
    estabelecimento:      Mapped[Optional["Estabelecimento"]]           = relationship("Estabelecimento", back_populates="transacoes")
    categoria:            Mapped[Optional["Categoria"]]                 = relationship("Categoria", foreign_keys=[categoria_id])
    subcategoria:         Mapped[Optional["Subcategoria"]]              = relationship("Subcategoria", foreign_keys=[subcategoria_id])
    categoria_sugerida:   Mapped[Optional["Categoria"]]                 = relationship("Categoria", foreign_keys=[categoria_sugerida_id])
    subcategoria_sugerida: Mapped[Optional["Subcategoria"]]             = relationship("Subcategoria", foreign_keys=[subcategoria_sugerida_id])
    alocacoes:            Mapped[list["TransacaoAlocacaoCategoria"]]    = relationship("TransacaoAlocacaoCategoria", back_populates="transacao")
    logs:                 Mapped[list["LogClassificacao"]]              = relationship("LogClassificacao", back_populates="transacao")
    feedbacks:            Mapped[list["Feedback"]]                      = relationship("Feedback", back_populates="transacao")
    confirmacoes:         Mapped[list["ConfirmacaoCategoriaMarketplace"]] = relationship(
        "ConfirmacaoCategoriaMarketplace", back_populates="transacao"
    )


# ----
# ALOCAÇÕES MULTICATEGORIA POR TRANSAÇÃO
# ----

class TransacaoAlocacaoCategoria(Base):
    __tablename__ = "transacao_alocacoes_categoria"
    __table_args__ = (
        UniqueConstraint("transacao_id", "categoria_id", "subcategoria_id"),
        CheckConstraint("valor_alocado >= 0"),
        CheckConstraint("percentual_alocado >= 0 AND percentual_alocado <= 100"),
        CheckConstraint("confianca BETWEEN 0 AND 1"),
        CheckConstraint(
            "fonte IN ("
            "'usuario','nota_fiscal','email','api_marketplace',"
            "'historico_usuario','llm','estimativa')"
        ),
    )

    id:                 Mapped[int]             = mapped_column(Integer, primary_key=True, autoincrement=True)
    transacao_id:       Mapped[int]             = mapped_column(ForeignKey("transacoes.id", ondelete="CASCADE"), nullable=False)
    categoria_id:       Mapped[int]             = mapped_column(ForeignKey("categorias.id"), nullable=False)
    subcategoria_id:    Mapped[Optional[int]]   = mapped_column(ForeignKey("subcategorias.id"))
    valor_alocado:      Mapped[Decimal]         = mapped_column(Numeric(12, 2), nullable=False)
    percentual_alocado: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 4))
    confianca:          Mapped[Decimal]         = mapped_column(Numeric(4, 3), nullable=False, default=Decimal("1.0"))
    fonte:              Mapped[str]             = mapped_column(Text, nullable=False)
    confirmado:         Mapped[bool]            = mapped_column(Boolean, nullable=False, default=False)
    observacao:         Mapped[Optional[str]]   = mapped_column(Text)
    criado_em:          Mapped[datetime]        = mapped_column(nullable=False, server_default=func.now())
    atualizado_em:      Mapped[datetime]        = mapped_column(nullable=False, server_default=func.now())

    transacao:    Mapped["Transacao"]           = relationship("Transacao", back_populates="alocacoes")
    categoria:    Mapped["Categoria"]           = relationship("Categoria", foreign_keys=[categoria_id])
    subcategoria: Mapped[Optional["Subcategoria"]] = relationship("Subcategoria", foreign_keys=[subcategoria_id])


# ----
# SUGESTÕES DE CATEGORIA POR USUÁRIO (marketplace)
# ----

class SugestaoCategoriaMarketplace(Base):
    __tablename__ = "sugestoes_categoria_marketplace"
    __table_args__ = (
        UniqueConstraint("usuario_id", "estabelecimento_id", "categoria_id", "subcategoria_id"),
        CheckConstraint("quantidade_confirmada >= 0"),
        CheckConstraint("quantidade_sugerida >= 0"),
        CheckConstraint("confianca_historica BETWEEN 0 AND 1"),
    )

    id:                    Mapped[int]              = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id:            Mapped[int]              = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    estabelecimento_id:    Mapped[int]              = mapped_column(ForeignKey("estabelecimentos.id", ondelete="CASCADE"), nullable=False)
    categoria_id:          Mapped[int]              = mapped_column(ForeignKey("categorias.id"), nullable=False)
    subcategoria_id:       Mapped[Optional[int]]    = mapped_column(ForeignKey("subcategorias.id"))
    quantidade_confirmada: Mapped[int]              = mapped_column(Integer, nullable=False, default=0)
    quantidade_sugerida:   Mapped[int]              = mapped_column(Integer, nullable=False, default=0)
    confianca_historica:   Mapped[Decimal]          = mapped_column(Numeric(4, 3), nullable=False, default=Decimal("0.0"))
    primeira_ocorrencia:   Mapped[Optional[datetime]] = mapped_column()
    ultima_ocorrencia:     Mapped[Optional[datetime]] = mapped_column()
    atualizado_em:         Mapped[datetime]         = mapped_column(nullable=False, server_default=func.now())

    usuario:         Mapped["Usuario"]              = relationship("Usuario", back_populates="sugestoes_marketplace")
    estabelecimento: Mapped["Estabelecimento"]      = relationship("Estabelecimento", back_populates="sugestoes_marketplace")
    categoria:       Mapped["Categoria"]            = relationship("Categoria", foreign_keys=[categoria_id])
    subcategoria:    Mapped[Optional["Subcategoria"]] = relationship("Subcategoria", foreign_keys=[subcategoria_id])


# ----
# CONFIRMAÇÕES DE CATEGORIA (marketplace)
# ----

class ConfirmacaoCategoriaMarketplace(Base):
    __tablename__ = "confirmacoes_categoria_marketplace"
    __table_args__ = (
        UniqueConstraint("usuario_id", "transacao_id", "categoria_id", "subcategoria_id"),
    )

    id:                 Mapped[int]             = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id:         Mapped[int]             = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    transacao_id:       Mapped[int]             = mapped_column(ForeignKey("transacoes.id", ondelete="CASCADE"), nullable=False)
    estabelecimento_id: Mapped[int]             = mapped_column(ForeignKey("estabelecimentos.id"), nullable=False)
    categoria_id:       Mapped[int]             = mapped_column(ForeignKey("categorias.id"), nullable=False)
    subcategoria_id:    Mapped[Optional[int]]   = mapped_column(ForeignKey("subcategorias.id"))
    valor_confirmado:   Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    confirmado_em:      Mapped[datetime]        = mapped_column(nullable=False, server_default=func.now())

    usuario:         Mapped["Usuario"]              = relationship("Usuario", back_populates="confirmacoes")
    transacao:       Mapped["Transacao"]            = relationship("Transacao", back_populates="confirmacoes")
    estabelecimento: Mapped["Estabelecimento"]      = relationship("Estabelecimento")
    categoria:       Mapped["Categoria"]            = relationship("Categoria", foreign_keys=[categoria_id])
    subcategoria:    Mapped[Optional["Subcategoria"]] = relationship("Subcategoria", foreign_keys=[subcategoria_id])


# ----
# LOG DE CLASSIFICAÇÕES
# ----

class LogClassificacao(Base):
    __tablename__ = "log_classificacoes"

    id:                    Mapped[int]              = mapped_column(Integer, primary_key=True, autoincrement=True)
    transacao_id:          Mapped[int]              = mapped_column(ForeignKey("transacoes.id", ondelete="CASCADE"), nullable=False)
    nome_entrada:          Mapped[str]              = mapped_column(Text, nullable=False)
    categoria_sugerida:    Mapped[Optional[str]]    = mapped_column(Text)
    subcategoria_sugerida: Mapped[Optional[str]]    = mapped_column(Text)
    confianca:             Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))
    metodo:                Mapped[Optional[str]]    = mapped_column(Text)  # 'cache', 'vetorial', 'llm'
    prompt_usado:          Mapped[Optional[str]]    = mapped_column(Text)
    resposta_llm:          Mapped[Optional[str]]    = mapped_column(Text)
    similaridade:          Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))
    tempo_ms:              Mapped[Optional[int]]    = mapped_column(Integer)
    criado_em:             Mapped[Optional[datetime]] = mapped_column(server_default=func.now())

    transacao: Mapped["Transacao"] = relationship("Transacao", back_populates="logs")


# ----
# FEEDBACKS DO USUÁRIO
# ----

class Feedback(Base):
    __tablename__ = "feedbacks"

    id:                        Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    transacao_id:              Mapped[int]           = mapped_column(ForeignKey("transacoes.id", ondelete="CASCADE"), nullable=False)
    usuario_id:                Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"))
    categoria_original_id:     Mapped[Optional[int]] = mapped_column(ForeignKey("categorias.id"))
    categoria_corrigida_id:    Mapped[int]           = mapped_column(ForeignKey("categorias.id"), nullable=False)
    subcategoria_corrigida_id: Mapped[Optional[int]] = mapped_column(ForeignKey("subcategorias.id"))
    observacao:                Mapped[Optional[str]] = mapped_column(Text)
    criado_em:                 Mapped[Optional[datetime]] = mapped_column(server_default=func.now())

    transacao:              Mapped["Transacao"]              = relationship("Transacao", back_populates="feedbacks")
    usuario:                Mapped[Optional["Usuario"]]      = relationship("Usuario")
    categoria_original:     Mapped[Optional["Categoria"]]   = relationship("Categoria", foreign_keys=[categoria_original_id])
    categoria_corrigida:    Mapped["Categoria"]             = relationship("Categoria", foreign_keys=[categoria_corrigida_id])
    subcategoria_corrigida: Mapped[Optional["Subcategoria"]] = relationship("Subcategoria", foreign_keys=[subcategoria_corrigida_id])


# ----
# ALIASES DE ESTABELECIMENTO
# ----

class EstabelecimentoAlias(Base):
    __tablename__ = "estabelecimento_aliases"
    __table_args__ = (
        UniqueConstraint(
            "estabelecimento_id",
            "alias_normalizado",
            name="uq_estabelecimento_alias",
        ),
    )

    id:                 Mapped[int]  = mapped_column(Integer, primary_key=True, autoincrement=True)
    estabelecimento_id: Mapped[int]  = mapped_column(
        ForeignKey("estabelecimentos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alias_normalizado:  Mapped[str]  = mapped_column(String, nullable=False)
    tipo_match:         Mapped[str]  = mapped_column(String(20), nullable=False, default="exato")
    prioridade:         Mapped[int]  = mapped_column(SmallInteger, nullable=False, default=100)
    ativo:              Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em:          Mapped[Optional[datetime]] = mapped_column(server_default=func.now())
    atualizado_em:      Mapped[Optional[datetime]] = mapped_column(server_default=func.now())

    estabelecimento: Mapped["Estabelecimento"] = relationship(
        "Estabelecimento", back_populates="aliases"
    )
