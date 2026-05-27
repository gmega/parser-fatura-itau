"""Deterministic OFX (Open Financial Exchange) statement extractor.

Emits the same Transaction schema as itau_parser so the two CSVs can be
merged for downstream expense analysis. OFX has no concept of card or
category, so those fields stay blank.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# Itaú emits OFX 1.x (SGML) with the CHARSET:1252 header. Decode permissively.
_ENCODING = "latin-1"

_STMTTRN_RE = re.compile(r"<STMTTRN>(.*?)</STMTTRN>", re.DOTALL)
_FIELD_RE = re.compile(r"<([A-Z]+)>\s*([^\r\n<]*?)\s*(?=\r?\n|<|$)")
_CURDEF_RE = re.compile(r"<CURDEF>\s*([A-Z]{3})")
_ACCTID_RE = re.compile(r"<ACCTID>\s*(\S+)")


@dataclass
class Transaction:
    cartao: str
    data: str
    descricao: str
    categoria: str
    valor: str
    moeda: str


def extract_transactions(ofx_path: str | Path) -> list[Transaction]:
    raw = Path(ofx_path).read_text(encoding=_ENCODING)
    curdef = _CURDEF_RE.search(raw)
    moeda = curdef.group(1) if curdef else ""
    acctid = _ACCTID_RE.search(raw)
    cartao = f"CC-{acctid.group(1)}" if acctid else ""

    out: list[Transaction] = []
    for block in _STMTTRN_RE.finditer(raw):
        fields = dict(_FIELD_RE.findall(block.group(1)))
        out.append(Transaction(
            cartao=cartao,
            data=_format_date(fields.get("DTPOSTED", "")),
            descricao=fields.get("MEMO", "").strip(),
            categoria="",
            valor=fields.get("TRNAMT", "").strip(),
            moeda=moeda,
        ))
    return out


def to_csv(transactions: Iterable[Transaction], out_path: str | Path) -> None:
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["cartão", "data", "descrição", "categoria", "valor", "moeda"])
        for t in transactions:
            writer.writerow([t.cartao, t.data, t.descricao, t.categoria, t.valor, t.moeda])


def _format_date(dtposted: str) -> str:
    m = re.match(r"(\d{4})(\d{2})(\d{2})", dtposted)
    if not m:
        return ""
    year, month, day = m.groups()
    return f"{year}-{month}-{day}"


def _main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Extract Itaú OFX statement to CSV.")
    parser.add_argument("ofx", help="Path to the .ofx file")
    parser.add_argument("-o", "--output", default="-", help="Output CSV path (default stdout)")
    args = parser.parse_args()
    txns = extract_transactions(args.ofx)
    if args.output == "-":
        import sys
        writer = csv.writer(sys.stdout)
        writer.writerow(["cartão", "data", "descrição", "categoria", "valor", "moeda"])
        for t in txns:
            writer.writerow([t.cartao, t.data, t.descricao, t.categoria, t.valor, t.moeda])
    else:
        to_csv(txns, args.output)


if __name__ == "__main__":
    _main()
