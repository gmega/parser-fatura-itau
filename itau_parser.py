"""Deterministic extractor for Itaú credit-card PDF statements.

Reads a PDF, splits each page into two columns by x-coordinate, walks the
resulting line stream as a state machine, and emits one Transaction per
purchase. International (USD) transactions are detected by the "Dólar de
Conversão" trailer and the value is taken as the USD-equivalent figure on
the second line.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Iterator

import pdfplumber


# Geometry: tuned to fatura-02. The left column's rightmost content is
# the value at x≈322-331; the right column's first content is the date
# at x≈370.8. Any split in between cleanly separates them.
_COLUMN_SPLIT_X = 350.0
_ROW_TOLERANCE = 2.0


# A money amount, with Brazilian formatting: optional minus, optional
# thousands separator, two decimals. Examples: "8,50", "1.539,00", "- 773,00".
_MONEY = r"-?\s?\d{1,3}(?:\.\d{3})*,\d{2}"
_DATE = r"\d{2}/\d{2}"

_NATIONAL_LINE_RE = re.compile(rf"^({_DATE})\s+(.+?)\s+({_MONEY})$")
_INTERNATIONAL_LINE_RE = re.compile(rf"^({_DATE})\s+(.+?)\s+({_MONEY})$")
# Second line of an international transaction:
#   "ANTHROPIC.COM 110,00 BRL 20,70"
#   "VENICE.AI 18,00 USD 18,00"
_INTL_CONV_RE = re.compile(rf"^(.+?)\s+({_MONEY})\s+(USD|BRL|EUR)\s+({_MONEY})$")

_CARD_HEADER_RE = re.compile(r"\(final (\d{4})\)")
_NATIONAL_SUBTOTAL_RE = re.compile(r"^Lançamentos no cartão \(final (\d{4})\)")
_DOLAR_CONV_RE = re.compile(r"^Dólar de Conversão")

# Section markers we use to switch state or stop.
_NATIONAL_SECTION = "Lançamentos: compras e saques"
_INTERNATIONAL_SECTION = "Lançamentos internacionais"

# Anything from these markers onward is ignored.
_STOP_MARKERS = (
    "Lançamentos: produtos e serviços",
    "Compras parceladas - próximas faturas",
    "Encargos cobrados nesta fatura",
    "Simulação de Compras",
    "Simulação Saque Cash",
    "Demais Taxas de Juros",
    "Limites de crédito",
)


@dataclass
class Transaction:
    cartao: str
    data: str
    descricao: str
    categoria: str
    valor: str
    moeda: str


def extract_transactions(pdf_path: str | Path) -> list[Transaction]:
    lines = _extract_lines(Path(pdf_path))
    return list(_parse(lines))


def to_csv(transactions: Iterable[Transaction], out_path: str | Path) -> None:
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["cartão", "data", "descrição", "categoria", "valor", "moeda"])
        for t in transactions:
            writer.writerow([t.cartao, t.data, t.descricao, t.categoria, t.valor, t.moeda])


def _extract_lines(pdf_path: Path) -> list[str]:
    """Return the document's text as a list of lines, reading the left
    column of each page before the right column. Within a column, lines
    are ordered top-to-bottom."""
    out: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(use_text_flow=False)
            left = [w for w in words if w["x0"] < _COLUMN_SPLIT_X]
            right = [w for w in words if w["x0"] >= _COLUMN_SPLIT_X]
            out.extend(_words_to_lines(left))
            out.extend(_words_to_lines(right))
    return out


def _words_to_lines(words: list[dict]) -> list[str]:
    """Group words by their `top` coordinate (with a small tolerance),
    then join each group with single spaces in x order."""
    if not words:
        return []
    words = sorted(words, key=lambda w: (w["top"], w["x0"]))
    rows: list[list[dict]] = []
    current: list[dict] = [words[0]]
    for w in words[1:]:
        if abs(w["top"] - current[0]["top"]) <= _ROW_TOLERANCE:
            current.append(w)
        else:
            rows.append(current)
            current = [w]
    rows.append(current)
    return [
        " ".join(w["text"] for w in sorted(row, key=lambda w: w["x0"]))
        for row in rows
    ]


def _parse(lines: list[str]) -> Iterator[Transaction]:
    """State machine over the reconstructed line stream."""
    section: str | None = None  # "national" | "international" | None
    current_card: str | None = None
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].strip()

        if any(marker in line for marker in _STOP_MARKERS):
            return

        if _NATIONAL_SECTION in line:
            section = "national"
            i += 1
            continue

        if _INTERNATIONAL_SECTION in line:
            section = "international"
            i += 1
            continue

        # Card header — only changes the current card, doesn't itself
        # produce a transaction.
        m = _CARD_HEADER_RE.search(line)
        if m and not _NATIONAL_SUBTOTAL_RE.match(line):
            current_card = m.group(1)
            i += 1
            continue

        # Subtotal line "Lançamentos no cartão (final XXXX) <value>" —
        # end of that card's national block.
        if _NATIONAL_SUBTOTAL_RE.match(line):
            i += 1
            continue

        if section == "national" and current_card is not None:
            txn = _try_parse_national(lines, i, current_card)
            if txn is not None:
                yield txn
                i += 2
                continue

        if section == "international" and current_card is not None:
            txn = _try_parse_international(lines, i, current_card)
            if txn is not None:
                yield txn
                i += 3
                continue

        i += 1


def _try_parse_national(lines: list[str], i: int, card: str) -> Transaction | None:
    if i + 1 >= len(lines):
        return None
    m = _NATIONAL_LINE_RE.match(lines[i].strip())
    if not m:
        return None
    data, descricao, valor = m.group(1), m.group(2).strip(), _clean_money(m.group(3))
    categoria = lines[i + 1].strip()
    # The category line must not itself look like a transaction header
    # or another section marker — guard against parsing misalignment.
    if _NATIONAL_LINE_RE.match(categoria) or any(
        marker in categoria for marker in _STOP_MARKERS
    ):
        return None
    return Transaction(
        cartao=card,
        data=data,
        descricao=descricao,
        categoria=categoria,
        valor=valor,
        moeda="BRL",
    )


def _try_parse_international(lines: list[str], i: int, card: str) -> Transaction | None:
    if i + 2 >= len(lines):
        return None
    m1 = _INTERNATIONAL_LINE_RE.match(lines[i].strip())
    if not m1:
        return None
    m2 = _INTL_CONV_RE.match(lines[i + 1].strip())
    if not m2:
        return None
    if not _DOLAR_CONV_RE.match(lines[i + 2].strip()):
        return None
    data = m1.group(1)
    descricao = m1.group(2).strip()
    domain = m2.group(1).strip()
    usd_value = _clean_money(m2.group(4))
    return Transaction(
        cartao=card,
        data=data,
        descricao=descricao,
        categoria=domain,
        valor=usd_value,
        moeda="USD",
    )


def _clean_money(s: str) -> str:
    return re.sub(r"\s+", "", s)


def _main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Extract Itaú PDF statement to CSV.")
    parser.add_argument("pdf", help="Path to the fatura PDF")
    parser.add_argument("-o", "--output", default="-", help="Output CSV path (default stdout)")
    args = parser.parse_args()
    txns = extract_transactions(args.pdf)
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
