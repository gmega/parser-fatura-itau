import csv
import subprocess
import sys
from pathlib import Path

import cli
from itau import parser_cartao, parser_extrato
from itau.common import FONTE_CARTAO, FONTE_EXTRATO, CSV_FIELDS


ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "examples" / "fatura-02.pdf"
OFX = ROOT / "examples" / "extrato.ofx"
CLI = ROOT / "cli.py"


def _read_rows(path: Path) -> list[list[str]]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


def test_merge_function_yields_all_pdf_then_all_ofx():
    pdf_txns = list(parser_cartao.parse(PDF))
    ofx_txns = list(parser_extrato.parse(OFX))

    merged = list(cli.merge([PDF], [OFX]))

    assert len(merged) == len(pdf_txns) + len(ofx_txns)
    assert merged[: len(pdf_txns)] == pdf_txns
    assert merged[len(pdf_txns):] == ofx_txns


def test_merge_function_handles_pdf_only():
    merged = list(cli.merge(pdf_paths=[PDF]))
    assert all(t["fonte"] == FONTE_CARTAO for t in merged)
    assert len(merged) > 0


def test_merge_function_handles_ofx_only():
    merged = list(cli.merge(ofx_paths=[OFX]))
    assert all(t["fonte"] == FONTE_EXTRATO for t in merged)
    assert len(merged) > 0


def test_merge_function_supports_multiple_pdfs_and_ofxs():
    """Passing the same file twice should produce double the rows of
    that file — proves the driver iterates rather than dedupes."""
    one_pdf = list(cli.merge([PDF]))
    two_pdfs = list(cli.merge([PDF, PDF]))
    assert len(two_pdfs) == 2 * len(one_pdf)

    one_ofx = list(cli.merge(ofx_paths=[OFX]))
    two_ofxs = list(cli.merge(ofx_paths=[OFX, OFX]))
    assert len(two_ofxs) == 2 * len(one_ofx)


def test_cli_produces_merged_csv(tmp_path):
    out = tmp_path / "merged.csv"
    result = subprocess.run(
        [sys.executable, str(CLI),
         "--pdf", str(PDF), "--ofx", str(OFX), "-o", str(out)],
        capture_output=True, text=True, check=True, cwd=ROOT,
    )
    assert result.returncode == 0

    rows = _read_rows(out)
    assert tuple(rows[0]) == CSV_FIELDS

    for r in rows[1:]:
        assert len(r) == 7

    fontes = {r[-1] for r in rows[1:]}
    assert fontes == {FONTE_CARTAO, FONTE_EXTRATO}


def test_cli_errors_with_no_inputs(tmp_path):
    out = tmp_path / "merged.csv"
    result = subprocess.run(
        [sys.executable, str(CLI), "-o", str(out)],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode != 0
    assert "at least one" in result.stderr.lower()
    assert not out.exists()


def test_cli_pdf_only(tmp_path):
    out = tmp_path / "merged.csv"
    subprocess.run(
        [sys.executable, str(CLI),
         "--pdf", str(PDF), "-o", str(out)],
        check=True, capture_output=True, text=True, cwd=ROOT,
    )
    rows = _read_rows(out)
    fontes = {r[-1] for r in rows[1:]}
    assert fontes == {FONTE_CARTAO}


def test_cli_repeated_flags(tmp_path):
    """--pdf and --ofx are repeatable."""
    out = tmp_path / "merged.csv"
    subprocess.run(
        [sys.executable, str(CLI),
         "--pdf", str(PDF), "--pdf", str(PDF),
         "--ofx", str(OFX),
         "-o", str(out)],
        check=True, capture_output=True, text=True, cwd=ROOT,
    )
    rows = _read_rows(out)
    expected = 2 * len(list(parser_cartao.parse(PDF))) \
        + len(list(parser_extrato.parse(OFX)))
    assert len(rows) - 1 == expected
