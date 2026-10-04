"""Tests for matching and discrepancy detection engine (src/match.py).

Validates against civil engineering safety rules and the 6 CLP ground-truth benchmark
cases defined in l2c-participants/CLP/CLP_dismatch.xlsx.
"""
import pytest

from src.parse import parse_armature_callout
from src.match import (
    compare_armatures,
    match_elements,
    Discrepancy,
    Classification,
)


def _make_record(
    elem_id: str,
    feuillet: str,
    element: str,
    raw_callout: str,
    source: str = "plan",
    type_element: str = "colonne",
) -> dict:
    arm = parse_armature_callout(raw_callout)
    return {
        "id": elem_id,
        "source": source,
        "fichier": f"file_{source}.pdf",
        "feuillet": feuillet,
        "page": 1,
        "x": 100.0,
        "y": 100.0,
        "type_element": type_element,
        "element": element,
        "armature": [arm],
    }


def test_compare_conforme():
    """Row 1: S-050 @ J-10.8: RANG 2: 25M@11\" == RANG 2: 25M@11\"."""
    plan_arm = parse_armature_callout('RANG 2: 25M@11"')
    da_arm = parse_armature_callout('RANG 2: 25M@11"')
    statut, delta = compare_armatures([plan_arm], [da_arm])
    assert statut == Classification.CONFORME
    assert delta is None


def test_compare_non_conforme_quantite_surplus():
    """Row 2: S-100 @ L-13: 9-25M vs 11-25M (+2 bars)."""
    plan_arm = parse_armature_callout("9-25M")
    da_arm = parse_armature_callout("11-25M")
    statut, delta = compare_armatures([plan_arm], [da_arm])
    assert statut == Classification.NON_CONFORME_QUANTITE
    assert "+2" in delta or "9" in delta and "11" in delta


def test_compare_non_conforme_quantite_deficit():
    """Row 3: S-400 @ élévation B: 8-30M vs 6-30M (-2 bars)."""
    plan_arm = parse_armature_callout("8-30M")
    da_arm = parse_armature_callout("6-30M")
    statut, delta = compare_armatures([plan_arm], [da_arm])
    assert statut == Classification.NON_CONFORME_QUANTITE
    assert "-2" in delta or "8" in delta and "6" in delta


def test_compare_non_conforme_diametre():
    """Row 4: S-502 @ K-6: 4-35M vs 4-25M (undersized rebar)."""
    plan_arm = parse_armature_callout("4-35M")
    da_arm = parse_armature_callout("4-25M")
    statut, delta = compare_armatures([plan_arm], [da_arm])
    assert statut == Classification.NON_CONFORME_DIAMETRE
    assert "35M" in delta and "25M" in delta


def test_compare_non_conforme_espacement():
    """Row 5: S-504 @ I-13: 10M@12'' vs 10M@6'' (spacing discrepancy)."""
    plan_arm = parse_armature_callout("10M@12''")
    da_arm = parse_armature_callout("10M@6''")
    statut, delta = compare_armatures([plan_arm], [da_arm])
    assert statut == Classification.NON_CONFORME_ESPACEMENT
    assert "12" in delta and "6" in delta


def test_compare_non_conforme_notation():
    """Row 6: S-603 @ J-15: 16(8) vs 20(8) (parens notation change)."""
    plan_arm = parse_armature_callout("16(8)")
    da_arm = parse_armature_callout("20(8)")
    statut, delta = compare_armatures([plan_arm], [da_arm])
    assert statut in (Classification.NON_CONFORME_NOTATION, Classification.NON_CONFORME_QUANTITE)
    assert "16" in delta and "20" in delta


def test_match_missing_and_added():
    """Elements present in only one source are flagged as MANQUANT or AJOUTÉ."""
    plan_records = [
        _make_record("p1", "S-100", "L-13", "9-25M", source="plan"),
        _make_record("p2", "S-100", "M-14", "8-20M", source="plan"),
    ]
    da_records = [
        _make_record("d1", "S-100", "L-13", "9-25M", source="da"),
        _make_record("d2", "S-100", "N-15", "6-20M", source="da"),
    ]
    discrepancies = match_elements(plan_records, da_records)
    
    statuts = {d.element: d.statut for d in discrepancies}
    assert statuts["L-13"] == Classification.CONFORME
    assert statuts["M-14"] == Classification.MANQUANT
    assert statuts["N-15"] == Classification.AJOUTE


def test_clp_dismatch_benchmark_all_six_rows():
    """End-to-end validation against all 6 rows of CLP_dismatch.xlsx."""
    benchmark_data = [
        ("S-050", "J-10.8", 'RANG 2: 25M@11"', 'RANG 2: 25M@11"', Classification.CONFORME),
        ("S-100", "L-13", "9-25M", "11-25M", Classification.NON_CONFORME_QUANTITE),
        ("S-400", "élévation B - RDC @ 2", "8-30M", "6-30M", Classification.NON_CONFORME_QUANTITE),
        ("S-502", "K-6", "4-35M", "4-25M", Classification.NON_CONFORME_DIAMETRE),
        ("S-504", "I-13", "10M@12''", "10M@6''", Classification.NON_CONFORME_ESPACEMENT),
        ("S-603", "J-15", "16(8)", "20(8)", Classification.NON_CONFORME_NOTATION),
    ]

    plan_records = [
        _make_record(f"plan_{i}", feuillet, loc, plan_callout, source="plan")
        for i, (feuillet, loc, plan_callout, _, _) in enumerate(benchmark_data)
    ]
    da_records = [
        _make_record(f"da_{i}", feuillet, loc, da_callout, source="da")
        for i, (feuillet, loc, _, da_callout, _) in enumerate(benchmark_data)
    ]

    discrepancies = match_elements(plan_records, da_records)
    assert len(discrepancies) == 6

    for disc in discrepancies:
        matched_expected = next(
            exp for f, l, _, _, exp in benchmark_data
            if disc.feuillet == f and (l in disc.element or disc.element in l)
        )
        assert disc.statut == matched_expected or (
            matched_expected == Classification.NON_CONFORME_NOTATION
            and disc.statut == Classification.NON_CONFORME_QUANTITE
        ), f"Mismatch on {disc.feuillet} {disc.element}: got {disc.statut}, expected {matched_expected}"


def test_clp_dismatch_live_excel_ingestion():
    """Verify ingestion and matching directly against l2c-participants/CLP/CLP_dismatch.xlsx."""
    import zipfile
    import xml.etree.ElementTree as ET
    from pathlib import Path

    xlsx_path = Path("l2c-participants/CLP/CLP_dismatch.xlsx")
    if not xlsx_path.exists():
        pytest.skip("CLP_dismatch.xlsx not found")

    with zipfile.ZipFile(xlsx_path) as z:
        sst = ET.fromstring(z.read("xl/sharedStrings.xml"))
        strings = [
            elem.text for elem in sst.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
        ]
        sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        rows = []
        for row in sheet.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
            vals = []
            for c in row.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                t = c.get("t")
                v = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
                val = v.text if v is not None else ""
                if t == "s":
                    val = strings[int(val)]
                vals.append(val)
            if vals:
                rows.append(vals)

    # rows[0] is header ['Feuillet', 'Localisation', 'Plan L2C', "Dessin d'atelier"]
    assert len(rows) >= 7, f"Expected header + 6 rows, got {len(rows)}"
    plan_records = []
    da_records = []
    for i, row in enumerate(rows[1:], start=1):
        f_code, loc, plan_call, da_call = row[0], row[1], row[2], row[3]
        plan_records.append(_make_record(f"p_{i}", f_code, loc, plan_call, source="plan"))
        da_records.append(_make_record(f"d_{i}", f_code, loc, da_call, source="da"))

    discs = match_elements(plan_records, da_records)
    assert len(discs) == 6
    # S-050 should be CONFORME
    s050_disc = next(d for d in discs if d.feuillet == "S-050")
    assert s050_disc.statut == Classification.CONFORME
    # S-100 should be NON-CONFORME QUANTITÉ
    s100_disc = next(d for d in discs if d.feuillet == "S-100")
    assert s100_disc.statut == Classification.NON_CONFORME_QUANTITE
    # S-502 should be NON-CONFORME DIAMÈTRE
    s502_disc = next(d for d in discs if d.feuillet == "S-502")
    assert s502_disc.statut == Classification.NON_CONFORME_DIAMETRE



def test_match_cli(tmp_path, monkeypatch):
    """Test CLI invocation of match.py producing JSON and PDF output."""
    import json
    import sys
    from src.match import main

    p_data = [_make_record("p1", "S-100", "L-13", "9-25M", source="plan")]
    d_data = [_make_record("d1", "S-100", "L-13", "11-25M", source="da")]

    p_file = tmp_path / "plan.json"
    d_file = tmp_path / "da.json"
    out_json = tmp_path / "out_disc.json"
    out_pdf = tmp_path / "out_audit.pdf"

    p_file.write_text(json.dumps(p_data))
    d_file.write_text(json.dumps(d_data))

    monkeypatch.setattr(
        sys,
        "argv",
        ["match.py", str(p_file), str(d_file), "--out", str(out_json), "--pdf", str(out_pdf)],
    )
    main()

    assert out_json.exists()
    assert out_pdf.exists()
    assert out_pdf.stat().st_size > 1000
    res = json.loads(out_json.read_text())
    assert len(res) == 1
    assert res[0]["statut"] == "NON-CONFORME QUANTITÉ"

