from decimal import Decimal
from pathlib import Path

import pytest

from itau_parser import extract_transactions, to_csv


FATURA_PDF = Path(__file__).parent.parent / "examples" / "fatura-02.pdf"


@pytest.fixture(scope="module")
def transactions():
    return extract_transactions(FATURA_PDF)


def _brl_to_decimal(s: str) -> Decimal:
    # Negative values are rendered as "- 773,00" with a space; normalize.
    s = s.replace(" ", "").replace(".", "").replace(",", ".")
    return Decimal(s)


def find(transactions, *, cartao, data, descricao):
    matches = [
        t for t in transactions
        if t.cartao == cartao and t.data == data and t.descricao == descricao
    ]
    assert len(matches) == 1, f"expected 1 match for {cartao}/{data}/{descricao!r}, got {len(matches)}"
    return matches[0]


def test_first_three_transactions_card_9690(transactions):
    t1 = find(transactions, cartao="9690", data="14/11", descricao="HS PLAZA SUL 03/05")
    assert t1.categoria == "VESTUÁRIO .SAO PAULO"
    assert t1.valor == "119,95"
    assert t1.moeda == "BRL"

    t2 = find(transactions, cartao="9690", data="15/01", descricao="SAN MARINO PANIFICACA")
    assert t2.categoria == "ALIMENTAÇÃO .SAO PAULO"
    assert t2.valor == "8,50"
    assert t2.moeda == "BRL"

    t3 = find(transactions, cartao="9690", data="15/01", descricao="DELICIAS DO MOINHO")
    assert t3.categoria == "ALIMENTAÇÃO .SAO PAULO"
    assert t3.valor == "8,20"
    assert t3.moeda == "BRL"


def test_national_subtotal_card_9690(transactions):
    """The PDF reports 'Lançamentos no cartão (final 9690) 5.729,70'."""
    total = sum(
        _brl_to_decimal(t.valor)
        for t in transactions
        if t.cartao == "9690" and t.moeda == "BRL"
    )
    assert total == Decimal("5729.70")


def test_national_subtotal_card_1017(transactions):
    """The PDF reports 'Lançamentos no cartão (final 1017) 10.372,37'."""
    total = sum(
        _brl_to_decimal(t.valor)
        for t in transactions
        if t.cartao == "1017" and t.moeda == "BRL"
    )
    assert total == Decimal("10372.37")


def test_card_1017_first_transaction(transactions):
    t = find(transactions, cartao="1017", data="13/01", descricao="LATAM AIR*IKYTLO")
    assert t.valor == "5.790,02"
    assert t.moeda == "BRL"


def test_negative_value_handled(transactions):
    """One AMAZON BR line is negative (refund) — must be preserved."""
    matches = [
        t for t in transactions
        if t.cartao == "1017" and t.data == "14/01" and t.descricao == "AMAZON BR"
    ]
    assert len(matches) == 2
    values = sorted(t.valor for t in matches)
    assert values == ["-773,00", "773,00"]


def test_international_venice_card_9690(transactions):
    t = find(transactions, cartao="9690", data="20/01", descricao="VENICE.AI")
    assert t.moeda == "USD"
    assert t.valor == "18,00"


def test_international_claude_card_9690(transactions):
    """CLAUDE.AI was billed originally in BRL but charged via the international
    flow — the USD equivalent (last number on the second line) is what counts."""
    t = find(transactions, cartao="9690", data="22/01", descricao="CLAUDE.AI SUBSCRIPTION")
    assert t.moeda == "USD"
    assert t.valor == "20,70"


def test_international_amda_card_1017(transactions):
    t = find(transactions, cartao="1017", data="07/02", descricao="AMDA")
    assert t.moeda == "USD"
    assert t.valor == "92,96"


def test_no_transactions_from_ignored_sections(transactions):
    """Nothing after the international section's totals should appear —
    no 'Lançamentos: produtos e serviços', no 'Compras parceladas', etc."""
    forbidden = {
        "ANUIDADE DIFERENCI01/12",
        "ESTORNO DE ANUIDADE DIF",
        "DESCONTO NA FATURA - PO",
    }
    found = {t.descricao for t in transactions} & forbidden
    assert found == set(), f"found forbidden descriptions: {found}"


def test_csv_output_has_expected_header_and_first_row(transactions, tmp_path):
    out = tmp_path / "out.csv"
    to_csv(transactions, out)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "cartão,data,descrição,categoria,valor,moeda"
    # First row in extraction order should be a card 9690 transaction.
    # Just verify it has 6 fields and starts with 9690.
    first = lines[1].split(",")
    assert len(first) >= 6
    assert first[0] == "9690"


def test_determinism(transactions):
    """Running the extractor twice yields identical output."""
    again = extract_transactions(FATURA_PDF)
    assert [t.__dict__ for t in again] == [t.__dict__ for t in transactions]
