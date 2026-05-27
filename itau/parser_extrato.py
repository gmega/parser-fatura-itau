"""Deterministic OFX (Open Financial Exchange) statement extractor."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

from itau.common import FONTE_EXTRATO, Transaction, write_csv


# Itaú emits OFX 1.x (SGML) with the CHARSET:1252 header. Decode permissively.
_ENCODING = "latin-1"

_STMTTRN_RE = re.compile(r"<STMTTRN>(.*?)</STMTTRN>", re.DOTALL)
_FIELD_RE = re.compile(r"<([A-Z]+)>\s*([^\r\n<]*?)\s*(?=\r?\n|<|$)")
_CURDEF_RE = re.compile(r"<CURDEF>\s*([A-Z]{3})")
_ACCTID_RE = re.compile(r"<ACCTID>\s*(\S+)")


def parse(path: str | Path) -> Iterator[Transaction]:
    raw = Path(path).read_text(encoding=_ENCODING)
    curdef = _CURDEF_RE.search(raw)
    moeda = curdef.group(1) if curdef else ""
    acctid = _ACCTID_RE.search(raw)
    cartao = f"CC-{acctid.group(1)}" if acctid else ""

    for block in _STMTTRN_RE.finditer(raw):
        fields = dict(_FIELD_RE.findall(block.group(1)))
        yield Transaction(
            cartao=cartao,
            data=_format_date(fields.get("DTPOSTED", "")),
            descricao=fields.get("MEMO", "").strip(),
            categoria="",
            valor=fields.get("TRNAMT", "").strip(),
            moeda=moeda,
            fonte=FONTE_EXTRATO,
        )


def _format_date(dtposted: str) -> str:
    m = re.match(r"(\d{4})(\d{2})(\d{2})", dtposted)
    if not m:
        return ""
    year, month, day = m.groups()
    return f"{year}-{month}-{day}"


def _main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Extract Itaú OFX extrato to CSV.")
    p.add_argument("ofx", help="Path to the .ofx file")
    p.add_argument("-o", "--output", required=True, help="Output CSV path")
    args = p.parse_args()
    write_csv(parse(args.ofx), args.output)


if __name__ == "__main__":
    _main()
