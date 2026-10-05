"""
Etapa 10 — Verificação empírica da minimização de dados (LGPD), Seção 4.8 da monografia.

Conta, na base de produção (Postgres do agente), ocorrências de padrões de dados
sensíveis que a esteira de ingestão deve expurgar. Consulta somente leitura; nenhum
dado é exportado — apenas contagens agregadas são impressas e gravadas em
resultados/verificacao_lgpd.json.

Padrões verificados sobre os campos textuais persistidos (nome_original,
nome_normalizado, origem_detalhamento e log de classificações):
  - PAN de cartão: 13 a 19 dígitos contíguos, com ou sem separadores (espaço/hífen a cada 4);
  - CPF: 11 dígitos, com ou sem máscara (000.000.000-00);
  - CVV explícito: rótulo "cvv"/"cvc" seguido de 3-4 dígitos;
  - e-mail: padrão local@dominio.
Também verifica se as tabelas de identificação de titulares armazenam apenas
identificadores pseudonimizados (UUID/hash), e não CPF/nome em claro.
"""
from __future__ import annotations

import json
import re

from sqlalchemy import text

import common as C

PADROES = {
    "pan_cartao_13_19_digitos": r"(\d[ -]?){12,18}\d",
    "cpf_mascarado_ou_nao": r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b",
    "cvv_rotulado": r"\b(cvv|cvc)\D{0,3}\d{3,4}\b",
    "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
}

CAMPOS = [
    ("transacoes", "nome_original"),
    ("transacoes", "nome_normalizado"),
    ("transacoes", "origem_detalhamento"),
    ("estabelecimentos", "nome_original"),
    ("estabelecimentos", "nome_normalizado"),
]


def main():
    eng = C.engine_sync()
    out = {"tabelas": {}, "padroes": {}, "titulares": {}}
    with eng.connect() as con:
        # inventário das tabelas textuais verificadas
        for tabela, campo in CAMPOS:
            n = con.execute(text(f"select count(*) from {tabela} where {campo} is not null")).scalar()
            out["tabelas"][f"{tabela}.{campo}"] = int(n)

        # contagem de ocorrências por padrão (regex avaliada no próprio Postgres, case-insensitive)
        for nome, rx in PADROES.items():
            total = 0
            por_campo = {}
            for tabela, campo in CAMPOS:
                n = con.execute(
                    text(f"select count(*) from {tabela} where {campo} ~* :rx"), {"rx": rx}
                ).scalar()
                por_campo[f"{tabela}.{campo}"] = int(n)
                total += int(n)
            out["padroes"][nome] = {"total": total, "por_campo": por_campo}

        # log de classificações, se existir
        try:
            cols = [r[0] for r in con.execute(text(
                "select column_name from information_schema.columns "
                "where table_name='log_classificacoes' and data_type in ('text','character varying')"))]
            out["log_classificacoes_colunas_texto"] = cols
            for nome, rx in PADROES.items():
                n = 0
                for c in cols:
                    n += int(con.execute(text(f"select count(*) from log_classificacoes where {c} ~* :rx"), {"rx": rx}).scalar())
                out["padroes"][nome]["log_classificacoes"] = n
        except Exception as e:  # tabela ausente neste esquema
            out["log_classificacoes_colunas_texto"] = f"indisponivel: {str(e)[:80]}"

        # titulares: quais colunas existem na tabela de usuários e se há CPF/nome em claro
        try:
            cols = [r[0] for r in con.execute(text(
                "select column_name from information_schema.columns where table_name='usuarios'"))]
            out["titulares"]["colunas_usuarios"] = cols
            out["titulares"]["n_usuarios"] = int(con.execute(text("select count(*) from usuarios")).scalar())
            suspeitas = [c for c in cols if re.search(r"cpf|nome|email|telefone|endereco", c, re.I)]
            out["titulares"]["colunas_potencialmente_identificadoras"] = suspeitas
            for c in suspeitas:
                out["titulares"][f"{c}_cpf_em_claro"] = int(con.execute(
                    text(f"select count(*) from usuarios where cast({c} as text) ~* :rx"),
                    {"rx": PADROES["cpf_mascarado_ou_nao"]}).scalar())
        except Exception as e:
            out["titulares"]["erro"] = str(e)[:120]

    (C.RESULTS / "verificacao_lgpd.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
