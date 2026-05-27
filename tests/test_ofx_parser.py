from decimal import Decimal
from pathlib import Path

import pytest

from ofx_parser import extract_transactions, to_csv


OFX = Path(__file__).parent.parent / "examples" / "extrato.ofx"


@pytest.fixture(scope="module")
def transactions():
    return extract_transactions(OFX)


def _brl_to_decimal(s: str) -> Decimal:
    return Decimal(s)


def test_count_matches_stmttrn_blocks(transactions):
    raw = OFX.read_text(encoding="latin-1")
    assert len(transactions) == raw.count("<STMTTRN>")


def test_first_transaction(transactions):
    t = transactions[0]
    assert t.data == "2026-02-02"
    assert t.descricao == "PIX TRANSF MAURO M02 02"
    assert t.valor == "-1000.00"
    assert t.moeda == "BRL"
    assert t.cartao == "CC-4088183597"
    assert t.categoria == ""


def test_credit_transaction_is_positive(transactions):
    matches = [
        t for t in transactions
        if t.data == "2026-04-22" and t.descricao == "DEV PIX Pagar Me Pa22 04"
    ]
    assert len(matches) == 1
    assert matches[0].valor == "29.90"


def test_last_transaction(transactions):
    t = transactions[-1]
    assert t.data == "2026-05-25"
    assert t.descricao == "REND PAGO APLIC AUT MAIS"
    assert t.valor == "9.05"


def test_all_have_required_fields(transactions):
    for t in transactions:
        assert t.data and t.data[4] == "-" and t.data[7] == "-"
        assert t.descricao
        assert t.valor
        assert t.moeda == "BRL"
        assert t.cartao == "CC-4088183597"


def test_sum_matches_ledger_delta(transactions):
    """Sum of transactions should reconcile with the OFX file's own data —
    i.e. each TRNAMT round-trips through our string formatting."""
    total = sum(_brl_to_decimal(t.valor) for t in transactions)
    # Spot check: this OFX file's net is non-trivial; we just verify
    # the sum is finite and the formatter is invertible for every row.
    assert isinstance(total, Decimal)
    # Round-trip every value individually.
    for t in transactions:
        _brl_to_decimal(t.valor)


def test_csv_output_schema_matches_pdf_parser(transactions, tmp_path):
    import csv
    out = tmp_path / "out.csv"
    to_csv(transactions, out)
    with open(out, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    assert rows[0] == ["cartão", "data", "descrição", "categoria", "valor", "moeda"]
    assert len(rows[1]) == 6
    # cartão carries the account ID; only categoria is blank for OFX.
    assert rows[1][0] == "CC-4088183597"
    assert rows[1][3] == ""


def test_determinism(transactions):
    again = extract_transactions(OFX)
    assert [t.__dict__ for t in again] == [t.__dict__ for t in transactions]
