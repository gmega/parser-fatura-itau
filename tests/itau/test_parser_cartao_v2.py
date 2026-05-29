"""Tests for the newer Itaú fatura PDF layout.

The newer template ships non-tabular text with no inter-word spaces
("Lançamentos:comprasesaques" instead of "Lançamentos: compras e saques")
and occasionally lets a domain abut the price on international rows
("ANTHROPIC.COM110,00 BRL 22,20"). The parser must handle both.
"""
from decimal import Decimal
from pathlib import Path

import pytest

from itau import parser_cartao
from itau.common import FONTE_CARTAO


FATURA_PDF = Path(__file__).resolve().parents[2] / "examples" / "fixture_b.pdf"


@pytest.fixture(scope="module")
def transactions():
    return list(parser_cartao.parse(FATURA_PDF))


def find(transactions, *, cartao, data, descricao):
    matches = [
        t for t in transactions
        if t["cartao"] == cartao and t["data"] == data and t["descricao"] == descricao
    ]
    assert len(matches) == 1, f"expected 1 match for {cartao}/{data}/{descricao!r}, got {len(matches)}"
    return matches[0]


def test_national_subtotal_card_9690(transactions):
    total = sum(
        Decimal(t["valor"])
        for t in transactions
        if t["cartao"] == "9690" and t["moeda"] == "BRL"
    )
    assert total == Decimal("-8050.34")


def test_national_subtotal_card_4740(transactions):
    total = sum(
        Decimal(t["valor"])
        for t in transactions
        if t["cartao"] == "4740" and t["moeda"] == "BRL"
    )
    assert total == Decimal("-762.86")


def test_national_subtotal_card_1017(transactions):
    total = sum(
        Decimal(t["valor"])
        for t in transactions
        if t["cartao"] == "1017" and t["moeda"] == "BRL"
    )
    assert total == Decimal("-3666.72")


def test_pre_emission_year_inference(transactions):
    """A 02/03 charge on a fatura emitted in May 2026 should resolve to
    2026, not 2025 — the month is before the emission month."""
    t = find(transactions, cartao="9690", data="2026-03-02", descricao="HSPLAZASUL 03/10")
    assert t["valor"] == "-171.00"
    assert t["categoria"] == "VESTUÁRIO.SAOPAULO"


def test_card_4740_transactions(transactions):
    """4740 is a new card in this fatura — verify both rows parse."""
    rows_4740 = [t for t in transactions if t["cartao"] == "4740"]
    assert len(rows_4740) == 2
    values = sorted(Decimal(t["valor"]) for t in rows_4740)
    assert values == [Decimal("-591.38"), Decimal("-171.48")]


def test_international_windsurf_card_9690(transactions):
    t = find(transactions, cartao="9690", data="2026-04-13", descricao="WINDSURF")
    assert t["moeda"] == "USD"
    assert t["valor"] == "-15.00"
    assert t["categoria"] == "WINDSURF.COM"


def test_international_claude_no_space_before_amount(transactions):
    """In fatura-05 the Anthropic row reads "ANTHROPIC.COM110,00 BRL 22,20"
    with no whitespace between domain and amount — the intl regex must
    handle that."""
    t = find(transactions, cartao="9690", data="2026-04-22", descricao="CLAUDE.AISUBSCRIPTION")
    assert t["moeda"] == "USD"
    assert t["valor"] == "-22.20"
    assert t["categoria"] == "ANTHROPIC.COM"


def test_international_card_1017(transactions):
    intl_1017 = [t for t in transactions if t["cartao"] == "1017" and t["moeda"] == "USD"]
    assert len(intl_1017) == 2
    values = sorted(Decimal(t["valor"]) for t in intl_1017)
    assert values == [Decimal("-17.80"), Decimal("-16.16")]


def test_total_transaction_count(transactions):
    assert len(transactions) == 146


def test_all_rows_have_fonte_cartao(transactions):
    assert all(t["fonte"] == FONTE_CARTAO for t in transactions)


def test_no_transactions_from_ignored_sections(transactions):
    """Lines under "Compras parceladas - próximas faturas" repeat installment
    rows and must not be picked up."""
    parcel_repeats = [
        t for t in transactions
        if t["descricao"] == "HSPLAZASUL 04/10" or t["descricao"] == "PORTOSEGURO 04/10"
    ]
    assert parcel_repeats == []


def test_determinism(transactions):
    again = list(parser_cartao.parse(FATURA_PDF))
    assert again == transactions
