from decimal import Decimal
from pathlib import Path

import pytest

import pdf_cartao_parser
from common import FONTE_CARTAO, CSV_FIELDS, write_csv


FATURA_PDF = Path(__file__).parent.parent / "examples" / "fatura-02.pdf"


@pytest.fixture(scope="module")
def transactions():
    return list(pdf_cartao_parser.parse(FATURA_PDF))


def find(transactions, *, cartao, data, descricao):
    matches = [
        t for t in transactions
        if t["cartao"] == cartao and t["data"] == data and t["descricao"] == descricao
    ]
    assert len(matches) == 1, f"expected 1 match for {cartao}/{data}/{descricao!r}, got {len(matches)}"
    return matches[0]


def test_first_three_transactions_card_9690(transactions):
    """Expenses on a credit card statement come out negative (cash leaving
    the holder's pocket); refunds come out positive."""
    t1 = find(transactions, cartao="9690", data="2025-11-14", descricao="HS PLAZA SUL 03/05")
    assert t1["categoria"] == "VESTUÁRIO .SAO PAULO"
    assert t1["valor"] == "-119.95"
    assert t1["moeda"] == "BRL"
    assert t1["fonte"] == FONTE_CARTAO

    t2 = find(transactions, cartao="9690", data="2026-01-15", descricao="SAN MARINO PANIFICACA")
    assert t2["categoria"] == "ALIMENTAÇÃO .SAO PAULO"
    assert t2["valor"] == "-8.50"

    t3 = find(transactions, cartao="9690", data="2026-01-15", descricao="DELICIAS DO MOINHO")
    assert t3["categoria"] == "ALIMENTAÇÃO .SAO PAULO"
    assert t3["valor"] == "-8.20"


def test_national_subtotal_card_9690(transactions):
    total = sum(
        Decimal(t["valor"])
        for t in transactions
        if t["cartao"] == "9690" and t["moeda"] == "BRL"
    )
    assert total == Decimal("-5729.70")


def test_national_subtotal_card_1017(transactions):
    total = sum(
        Decimal(t["valor"])
        for t in transactions
        if t["cartao"] == "1017" and t["moeda"] == "BRL"
    )
    assert total == Decimal("-10372.37")


def test_card_1017_first_transaction(transactions):
    t = find(transactions, cartao="1017", data="2026-01-13", descricao="LATAM AIR*IKYTLO")
    assert t["valor"] == "-5790.02"
    assert t["moeda"] == "BRL"


def test_negative_value_handled(transactions):
    matches = [
        t for t in transactions
        if t["cartao"] == "1017" and t["data"] == "2026-01-14" and t["descricao"] == "AMAZON BR"
    ]
    assert len(matches) == 2
    values = sorted(t["valor"] for t in matches)
    assert values == ["-773.00", "773.00"]


def test_international_venice_card_9690(transactions):
    t = find(transactions, cartao="9690", data="2026-01-20", descricao="VENICE.AI")
    assert t["moeda"] == "USD"
    assert t["valor"] == "-18.00"


def test_international_claude_card_9690(transactions):
    t = find(transactions, cartao="9690", data="2026-01-22", descricao="CLAUDE.AI SUBSCRIPTION")
    assert t["moeda"] == "USD"
    assert t["valor"] == "-20.70"


def test_international_amda_card_1017(transactions):
    t = find(transactions, cartao="1017", data="2026-02-07", descricao="AMDA")
    assert t["moeda"] == "USD"
    assert t["valor"] == "-92.96"


def test_no_transactions_from_ignored_sections(transactions):
    forbidden = {
        "ANUIDADE DIFERENCI01/12",
        "ESTORNO DE ANUIDADE DIF",
        "DESCONTO NA FATURA - PO",
    }
    found = {t["descricao"] for t in transactions} & forbidden
    assert found == set(), f"found forbidden descriptions: {found}"


def test_all_rows_have_fonte_cartao(transactions):
    assert all(t["fonte"] == FONTE_CARTAO for t in transactions)


def test_csv_output_has_expected_header_and_first_row(transactions, tmp_path):
    import csv
    out = tmp_path / "out.csv"
    write_csv(transactions, out)
    with open(out, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    assert tuple(rows[0]) == CSV_FIELDS
    assert rows[1][0] == "9690"
    assert rows[1][-1] == FONTE_CARTAO


def test_determinism(transactions):
    again = list(pdf_cartao_parser.parse(FATURA_PDF))
    assert again == transactions
