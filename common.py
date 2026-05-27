"""Shared types and helpers for transaction parsers.

A parser is any callable matching the `Parser` protocol below — it takes
a file path and returns an iterable of `Transaction` dicts in the shared
schema. The `fonte` field is set by the parser itself ("cartão" for
credit-card statements, "extrato" for bank statements), so consumers can
freely merge results from any combination of parsers.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Iterator, Protocol, TypedDict


FONTE_CARTAO = "cartão"
FONTE_EXTRATO = "extrato"


class Transaction(TypedDict):
    cartao: str
    data: str       # ISO YYYY-MM-DD
    descricao: str
    categoria: str
    valor: str      # ISO numeric, sign-normalized (outflows negative)
    moeda: str      # ISO 4217 currency code, e.g. "BRL", "USD"
    fonte: str      # FONTE_CARTAO | FONTE_EXTRATO


CSV_FIELDS: tuple[str, ...] = (
    "cartão", "data", "descrição", "categoria", "valor", "moeda", "fonte",
)


class Parser(Protocol):
    def __call__(self, path: str | Path) -> Iterator[Transaction]: ...


def write_csv(transactions: Iterable[Transaction], out_path: str | Path) -> None:
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_FIELDS)
        for t in transactions:
            writer.writerow([
                t["cartao"], t["data"], t["descricao"], t["categoria"],
                t["valor"], t["moeda"], t["fonte"],
            ])
