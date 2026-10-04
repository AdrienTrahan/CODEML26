import pytest
from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from extract import extract_page
from parse import parse_length_mm, parse_armature_callout, parse_tokens

REPO_ROOT = Path(__file__).resolve().parent.parent
PDF_BASE_DIR = (
    REPO_ROOT / "l2c-participants"
    if (REPO_ROOT / "l2c-participants").exists()
    else REPO_ROOT / "l2c-participants (1)"
)
CLP_PDF = PDF_BASE_DIR / "CLP" / "L2C_PLAN_STR_CLP.pdf"

requires_clp_pdf = pytest.mark.skipif(not CLP_PDF.exists(), reason="CLP PDF not available")


def test_parse_length_mm():
    # 15' - 10" = 15*304.8 + 10*25.4 = 4826.0 mm
    assert pytest.approx(parse_length_mm("15' - 10\""), 0.1) == 4826.0
    assert pytest.approx(parse_length_mm("15'-10\""), 0.1) == 4826.0
    assert pytest.approx(parse_length_mm("2' - 8\""), 0.1) == 812.8
    assert pytest.approx(parse_length_mm("16\""), 0.1) == 406.4
    assert pytest.approx(parse_length_mm("12\""), 0.1) == 304.8
    assert parse_length_mm("N/A") is None

def test_parse_armature_callout_qn_diam():
    arm = parse_armature_callout("17-25M")
    assert arm["quantite"] == 17
    assert arm["diametre"] == "25M"
    assert arm["raw"] == "17-25M"
    
    arm9 = parse_armature_callout("9-25M")
    assert arm9["quantite"] == 9
    assert arm9["diametre"] == "25M"
    assert arm9["raw"] == "9-25M"

def test_parse_armature_callout_at_esp():
    arm = parse_armature_callout("15M@16\" c/c")
    assert arm["diametre"] == "15M"
    assert pytest.approx(arm["espacement_mm"], 0.1) == 406.4
    assert arm["quantite"] is None

def test_parse_armature_callout_multiplier():
    arm = parse_armature_callout("2x4 30M")
    assert arm["quantite"] == 8
    assert arm["diametre"] == "30M"
    
    arm3 = parse_armature_callout("3x7 10M")
    assert arm3["quantite"] == 21
    assert arm3["diametre"] == "10M"

def test_canonicalize_grid():
    from parse import canonicalize_grid
    assert canonicalize_grid("B/1.8") == "B-1.8"
    assert canonicalize_grid("B-1.8") == "B-1.8"
    assert canonicalize_grid("B 1.8") == "B-1.8"
    assert canonicalize_grid("L-13") == "L-13"
    assert canonicalize_grid("B.2-35") == "B.2-35"

@requires_clp_pdf
def test_parse_tokens_clp_s100():
    words = extract_page(CLP_PDF, 4)
    records = parse_tokens(words, "L2C_PLAN_STR_CLP.pdf", "S-100", 4)
    assert isinstance(records, list)
    assert len(records) >= 7
    
    # Verify TYPE C ground truth (9-25M)
    type_c = [r for r in records if r["element"] == "TYPE C"]
    assert len(type_c) == 1, "TYPE C record should be extracted"
    rec_c = type_c[0]
    assert rec_c["type_element"] == "semelle"
    assert rec_c["source"] == "plan"
    assert rec_c["feuillet"] == "S-100"
    assert rec_c["page"] == 4
    
    # Both ARM. LONG. and ARM. TRANS. are 9-25M for TYPE C
    dias = [a["diametre"] for a in rec_c["armature"]]
    quantities = [a["quantite"] for a in rec_c["armature"]]
    assert "25M" in dias
    assert 9 in quantities
    
    # Check that plan callouts (like 15M@16" c/c or 2-15M TOUT AUTOUR) are extracted
    all_raws = [a["raw"] for r in records for a in r["armature"]]
    assert any("15M@16" in raw for raw in all_raws)
    assert any("2-15M" in raw for raw in all_raws)

@requires_clp_pdf
def test_parse_multi_series_ground_truths():
    # S-050 (Page 3) - J-10.8 with 25M@11"
    r3 = parse_tokens(extract_page(CLP_PDF, 3), CLP_PDF.name, "S-050", 3)
    hit3 = [r for r in r3 if "J-10.8" in r["element"] and any(a["diametre"] == "25M" for a in r["armature"])]
    assert len(hit3) >= 1

    # S-400 (Page 14) - 8-30M shear wall callouts
    r14 = parse_tokens(extract_page(CLP_PDF, 14), CLP_PDF.name, "S-400", 14)
    hit14 = [r for r in r14 if r["type_element"] == "refend" and any(a["diametre"] == "30M" and a["quantite"] == 8 for a in r["armature"])]
    assert len(hit14) >= 1

    # S-502 (Page 18) - 4-35M column schedule
    r18 = parse_tokens(extract_page(CLP_PDF, 18), CLP_PDF.name, "S-502", 18)
    hit18 = [r for r in r18 if r["type_element"] == "colonne" and any(a["diametre"] == "35M" and a["quantite"] == 4 for a in r["armature"])]
    assert len(hit18) >= 1

    # S-603 (Page 26) - J-15 with 16(8) slab notation
    r26 = parse_tokens(extract_page(CLP_PDF, 26), CLP_PDF.name, "S-603", 26)
    hit26 = [r for r in r26 if "J-15" in r["element"] and any(a["quantite"] == 16 for a in r["armature"])]
    assert len(hit26) >= 1

