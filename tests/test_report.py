import json
from pathlib import Path
import sys
import pytest

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from report import report, audit_report
from match import match_elements, Classification, Discrepancy

def test_report_generation(tmp_path):
    sample_data = [
        {
            "id": "CLP_S-100_p4_0001",
            "source": "plan",
            "fichier": "L2C_PLAN_STR_CLP.pdf",
            "feuillet": "S-100",
            "page": 4,
            "x": 2724.0,
            "y": 2233.7,
            "type_element": "semelle",
            "element": "TYPE C",
            "armature": [
                {
                    "raw": "9-25M",
                    "repere": "ARM. LONG.",
                    "diametre": "25M",
                    "quantite": 9,
                    "espacement_mm": None,
                    "longueur_mm": 3378.2,
                    "bbox": [2977.6, 2257.4, 2998.3, 2269.0]
                }
            ]
        }
    ]
    json_path = tmp_path / "CLP_S-100_plan.json"
    json_path.write_text(json.dumps(sample_data), encoding="utf-8")
    
    out_pdf = tmp_path / "CLP_S-100_report.pdf"
    res_path = report(json_path, out_pdf)
    assert res_path.exists()
    assert res_path.stat().st_size > 500


def test_audit_report_generation(tmp_path):
    discrepancies = [
        Discrepancy(
            feuillet="S-050",
            element="J-10.8",
            type_element="semelle",
            statut=Classification.CONFORME,
            delta=None,
            plan_callout='RANG 2: 25M@11"',
            da_callout='RANG 2: 25M@11"',
            confidence=1.0,
            plan_id="p1",
            da_id="d1",
        ),
        Discrepancy(
            feuillet="S-100",
            element="L-13",
            type_element="semelle",
            statut=Classification.NON_CONFORME_QUANTITE,
            delta="+2 barres (9 -> 11)",
            plan_callout="9-25M",
            da_callout="11-25M",
            confidence=1.0,
            plan_id="p2",
            da_id="d2",
        ),
        Discrepancy(
            feuillet="S-502",
            element="K-6",
            type_element="colonne",
            statut=Classification.NON_CONFORME_DIAMETRE,
            delta="Diamètre non-conforme: 35M -> 25M",
            plan_callout="4-35M",
            da_callout="4-25M",
            confidence=1.0,
            plan_id="p3",
            da_id="d3",
        ),
    ]

    out_pdf = tmp_path / "CLP_audit_report.pdf"
    res_path = audit_report(discrepancies, out_pdf)
    assert res_path.exists()
    assert res_path.stat().st_size > 1000

