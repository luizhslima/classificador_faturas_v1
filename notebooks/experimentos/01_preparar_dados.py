"""
Etapa 1 — Construção da base rotulada de referência e dos splits.

Fontes reais (pasta data/datasets):
  * C6 Bank  : 105 CSVs de fatura com categoria nativa do emissor  -> rotulagem de referência
  * Nubank   : 27 CSVs (date,title,amount) sem rótulo do emissor   -> rótulo só quando há
                regra léxica de alta precisão (usado como reforço amostral)

Saídas em data/processed/:
  base_rotulada.csv, split_treino.csv, split_validacao.csv, split_teste.csv,
  nubank_para_bd.csv  (todas as transações Nubank, para gravação/HITL na etapa do agente)
"""
from __future__ import annotations

import pandas as pd

import common as C


def main() -> None:
    c6 = C.carregar_c6_rotulado()
    c6 = c6.rename(columns={})
    c6["texto"] = c6["descricao"]

    nu = C.carregar_nubank_bruto()
    nu_rot = nu[nu["categoria_regra"].notna()].copy()
    nu_rot["categoria"] = nu_rot["categoria_regra"]
    nu_rot["categoria_id"] = nu_rot["categoria"].map(C.CAT_TO_ID)
    nu_rot["categoria_nativa"] = "(sem rótulo do emissor)"
    nu_rot["metodo_rotulo"] = "regra_lexical"
    nu_rot["parcela"] = None
    nu_rot["final_cartao"] = None
    nu_rot["texto"] = nu_rot["descricao"]
    nu_rot = nu_rot[c6.columns]

    base = pd.concat([c6, nu_rot], ignore_index=True)
    base = base.drop_duplicates(
        subset=["descricao", "valor", "parcela", "categoria"]
    ).reset_index(drop=True)

    # Limita a no máx. 12 lançamentos por estabelecimento para que o benchmark meça
    # amplitude (variedade de comércios) e não a frequência de um único merchant
    # dominante (ex.: "UBER* TRIP"). Também torna o split por grupo ~70/15/15.
    base["_chave"] = base["descricao"].map(C.chave_estabelecimento)
    base = (
        base.sample(frac=1.0, random_state=C.RANDOM_STATE)
        .groupby("_chave", group_keys=False)
        .head(12)
        .drop(columns=["_chave"])
        .reset_index(drop=True)
    )

    print(f"Base rotulada: {len(base)} transações  ({len(c6)} C6 + {len(nu_rot)} Nubank)")
    dist = base["categoria"].value_counts()
    print(dist)

    # categorias com pouquíssimos exemplos são agrupadas em 'Despesas Diversas / Outros'
    n_estab = base.groupby("categoria")["descricao"].apply(
        lambda s: s.map(C.chave_estabelecimento).nunique()
    )
    raras = dist[(dist < 8) | (n_estab < 2)].index.tolist()
    if raras:
        print(f"\n[aviso] categorias com amostragem insuficiente, agrupadas em 'Despesas Diversas / Outros': {raras}")
        base.loc[base["categoria"].isin(raras), "categoria_id"] = C.CAT_TO_ID["Despesas Diversas / Outros"]
        base.loc[base["categoria"].isin(raras), "categoria"] = "Despesas Diversas / Outros"

    base.to_csv(C.PROCESSED / "base_rotulada.csv", index=False)

    tr, val, test = C.split_estratificado(base)
    tr.to_csv(C.PROCESSED / "split_treino.csv", index=False)
    val.to_csv(C.PROCESSED / "split_validacao.csv", index=False)
    test.to_csv(C.PROCESSED / "split_teste.csv", index=False)
    print(f"\nsplits -> treino {len(tr)} | validação {len(val)} | teste {len(test)}")
    print("categorias presentes no teste:", sorted(test['categoria'].unique()))

    nu.to_csv(C.PROCESSED / "nubank_para_bd.csv", index=False)
    print(f"nubank_para_bd.csv: {len(nu)} transações")


if __name__ == "__main__":
    main()
