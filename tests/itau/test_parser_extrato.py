from decimal import Decimal
from pathlib import Path

import pytest

from itau import parser_extrato
from itau.common import FONTE_EXTRATO, CSV_FIELDS, write_csv


OFX = Path(__file__).resolve().parents[2] / "examples" / "extrato.ofx"


@pytest.fixture(scope="module")
def transactions():
    return list(parser_extrato.parse(OFX))


def test_count_matches_stmttrn_blocks(transactions):
    raw = OFX.read_text(encoding="latin-1")
    assert len(transactions) == raw.count("<STMTTRN>")


def test_first_transaction(transactions):
    t = transactions[0]
    assert t["data"] == "2026-02-02"
    assert t["descricao"] == "PIX TRANSF MAURO M02 02"
    assert t["valor"] == "-1000.00"
    assert t["moeda"] == "BRL"
    assert t["cartao"] == "CC-4088183597"
    assert t["categoria"] == ""
    assert t["fonte"] == FONTE_EXTRATO


def test_credit_transaction_is_positive(transactions):
    matches = [
        t for t in transactions
        if t["data"] == "2026-04-22" and t["descricao"] == "DEV PIX Pagar Me Pa22 04"
    ]
    assert len(matches) == 1
    assert matches[0]["valor"] == "29.90"


def test_last_transaction(transactions):
    t = transactions[-1]
    assert t["data"] == "2026-05-25"
    assert t["descricao"] == "REND PAGO APLIC AUT MAIS"
    assert t["valor"] == "9.05"


def test_all_have_required_fields(transactions):
    for t in transactions:
        assert t["data"] and t["data"][4] == "-" and t["data"][7] == "-"
        assert t["descricao"]
        assert t["valor"]
        assert t["moeda"] == "BRL"
        assert t["cartao"] == "CC-4088183597"
        assert t["fonte"] == FONTE_EXTRATO


def test_every_value_is_parseable_decimal(transactions):
    for t in transactions:
        Decimal(t["valor"])


def test_csv_output_schema(transactions, tmp_path):
    import csv
    out = tmp_path / "out.csv"
    write_csv(transactions, out)
    with open(out, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    assert tuple(rows[0]) == CSV_FIELDS
    assert len(rows[1]) == 7
    assert rows[1][0] == "CC-4088183597"
    assert rows[1][3] == ""
    assert rows[1][-1] == FONTE_EXTRATO


def test_determinism(transactions):
    again = list(parser_extrato.parse(OFX))
    assert again == transactions
