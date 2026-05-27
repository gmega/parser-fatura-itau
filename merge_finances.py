"""Merge any number of PDF cartão statements and OFX extratos into one CSV.

Each source contributes its own `fonte` value ("cartão" or "extrato"),
set by the parsers themselves. Rows are emitted in input order (PDFs in
the order given, then OFXs in the order given)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Iterator

import extrato_ofx_parser
import pdf_cartao_parser
from common import Transaction, write_csv


def merge(
    pdf_paths: Iterable[str | Path] = (),
    ofx_paths: Iterable[str | Path] = (),
) -> Iterator[Transaction]:
    for p in pdf_paths:
        yield from pdf_cartao_parser.parse(p)
    for p in ofx_paths:
        yield from extrato_ofx_parser.parse(p)


def _main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        description="Merge PDF cartão statements and OFX extratos into a single CSV."
    )
    p.add_argument(
        "--pdf", action="append", default=[], metavar="PATH",
        help="Path to a PDF credit-card statement. May be passed multiple times.",
    )
    p.add_argument(
        "--ofx", action="append", default=[], metavar="PATH",
        help="Path to an OFX bank statement. May be passed multiple times.",
    )
    p.add_argument(
        "-o", "--output", required=True,
        help="Output CSV path.",
    )
    args = p.parse_args(argv)

    if not args.pdf and not args.ofx:
        p.error("provide at least one --pdf or --ofx input")

    write_csv(merge(args.pdf, args.ofx), args.output)


if __name__ == "__main__":
    _main()
