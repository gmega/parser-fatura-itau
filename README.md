# itau-parser

[![CI](https://github.com/gmega/parser-fatura-itau/actions/workflows/ci.yml/badge.svg)](https://github.com/gmega/parser-fatura-itau/actions/workflows/ci.yml)

Deterministic parsers for Itaú statements. Reads a PDF credit-card
fatura and/or an OFX bank extrato, emits a unified CSV ready to load
into pandas / DuckDB / SQLite for expense analysis.

## Setup

```sh
pip install -r requirements.txt
```

## Usage

Merge any combination of PDFs and OFX files into one CSV:

```sh
python cli.py \
  --pdf examples/fatura-02.pdf \
  --ofx examples/extrato.ofx \
  -o merged.csv
```

Both flags are repeatable; at least one is required.

Or use each parser on its own:

```python
from itau import parser_cartao, parser_extrato
from itau.common import write_csv

txns = list(parser_cartao.parse("examples/fatura-02.pdf"))
write_csv(txns, "fatura.csv")
```

## CSV schema

| column     | description                                                    |
| ---------- | -------------------------------------------------------------- |
| cartão     | `9690` / `1017` for credit cards; `CC-<ACCTID>` for checking   |
| data       | ISO `YYYY-MM-DD`                                               |
| descrição  | merchant / counterparty (raw from the statement)               |
| categoria  | Itaú's MCC-derived category + city for PDF; empty for OFX      |
| valor      | ISO numeric, sign-normalized — **outflows negative**           |
| moeda      | ISO 4217 (`BRL`, `USD`)                                        |
| fonte      | `cartão` (PDF) or `extrato` (OFX)                              |

## Layout

```
itau/
  common.py           Transaction TypedDict, write_csv, FONTE_* constants
  parser_cartao.py    PDF cartão statement parser (column-aware extractor)
  parser_extrato.py   OFX extrato parser
cli.py                Merge driver
tests/
  test_cli.py
  itau/
    test_parser_cartao.py
    test_parser_extrato.py
examples/
  fatura-02.pdf       Sample PDF statement
  extrato.ofx         Sample OFX statement
```

Each parser exposes `parse(path) -> Iterator[Transaction]`. The shared
`Transaction` TypedDict (with `fonte` populated by the parser itself)
lets the driver concatenate freely.

## Tests

```sh
pytest tests/
```

## Known limitations

- **USD rows**: PDF international transactions report `valor` in USD
  (with `moeda=USD`), not converted to BRL. The PDF includes a
  `Dólar de Conversão` rate per transaction; merging into a single
  BRL total would need to apply it.
- **No dedup across sources**: if a credit-card payment appears as a
  debit in the OFX and also gets summarized in the PDF, both will be
  emitted. The current PDF parser only reads the transaction sections,
  so the page-1 payment summary is skipped — but future bills with
  refunds / anuidade lines could double-count.
- **PDF year inference**: the year for each transaction is derived
  from the statement's `Emissão:` date. If a bill ever showed a
  charge older than ~11 months that assumption would break.
- **Tuned to fatura-02 layout**: column-split geometry (`x=350`) is
  empirical. Other Itaú PDF templates may need adjustment.
