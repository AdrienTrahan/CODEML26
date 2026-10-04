"""Vérifie le pipeline utilisable depuis le notebook et la CLI."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from src.extract import extract_pdf, extract_page, detect_feuillet
from src.parse import parse_tokens
from src.validate import validate

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "l2c-participants/CLP/L2C_PLAN_STR_CLP.pdf"

pytestmark = pytest.mark.skipif(not PDF.exists(), reason="CLP PDF not available")


def test_feuillets_clp():
    # Les renvois à S-200 et S-000 ne doivent pas remplacer le cartouche.
    expected = [
        "S-003", "S-004", "S-050", *[f"S-{i}" for i in range(100, 109)],
        "S-300", "S-400", "S-401", *[f"S-{i}" for i in range(500, 506)],
        "S-600.a", "S-600.b", *[f"S-{i}" for i in range(601, 606)],
    ]
    actual = [detect_feuillet(extract_page(PDF, page)) for page in range(1, 29)]
    assert actual == expected


def test_extract_pdf_selected_pages():
    sheets = {4: "S-100", 14: "S-400", 18: "S-502", 26: "S-603"}
    expected = [
        record
        for page, sheet in sheets.items()
        for record in parse_tokens(extract_page(PDF, page), PDF.name, sheet, page)
    ]
    records = extract_pdf(PDF, pages=sheets)
    assert records == expected
    assert {record["page"] for record in records} == set(sheets)
    assert len({record["id"] for record in records}) == len(records)


@pytest.mark.parametrize("page", [0, 29])
def test_extract_pdf_invalid_page(page):
    with pytest.raises(ValueError, match="out of range"):
        extract_pdf(PDF, pages=[page])


def test_extract_cli(tmp_path):
    output = tmp_path / "export" / "plan.json"
    subprocess.run(
        [sys.executable, "-m", "src.extract", str(PDF), str(output), "--pages", "4"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    records = validate(output)
    type_c = next(record for record in records if record.element == "TYPE C")
    assert type_c.feuillet == "S-100"
    assert any(arm.diametre == "25M" and arm.quantite == 9 for arm in type_c.armature)
    assert json.loads(output.read_text(encoding="utf-8")) == extract_pdf(PDF, pages=[4])
