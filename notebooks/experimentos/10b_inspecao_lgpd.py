"""
Etapa 10b — Inspeção das ocorrências candidatas a número de cartão apontadas pela etapa 10.

Imprime as cadeias que casaram com o padrão de PAN (13 a 19 dígitos, com ou sem
separadores), MASCARANDO todos os dígitos exceto os 4 primeiros de cada sequência
numérica, para permitir julgar se são números de cartão (PAN) ou falsos positivos
(códigos de autorização, telefones, CNPJ etc.) sem expor o dado. Somente leitura.
"""
from __future__ import annotations

import re

from sqlalchemy import text

import common as C

RX_PAN = r"(\d[ -]?){12,18}\d"
CAMPOS = [("transacoes", "nome_original"), ("estabelecimentos", "nome_original"), ("estabelecimentos", "nome_normalizado")]


def mascarar(s: str) -> str:
    def _m(m):
        d = m.group(0)
        return d[:4] + re.sub(r"\d", "X", d[4:])
    return re.sub(r"\d[\d -]*\d", _m, s)


def luhn_ok(digs: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digs):
        n = int(ch)
        if alt:
            n *= 2
            if n > 9:
                n -= 9
        total += n
        alt = not alt
    return total % 10 == 0


def main():
    eng = C.engine_sync()
    with eng.connect() as con:
        for tabela, campo in CAMPOS:
            rows = con.execute(text(f"select {campo} from {tabela} where {campo} ~* :rx"), {"rx": RX_PAN}).fetchall()
            for (val,) in rows:
                seq = re.search(RX_PAN, val)
                digs = re.sub(r"\D", "", seq.group(0)) if seq else ""
                print(f"{tabela}.{campo}: '{mascarar(val)}' | len_digitos={len(digs)} | luhn={'ok' if digs and luhn_ok(digs) else 'falha'}")


if __name__ == "__main__":
    main()
