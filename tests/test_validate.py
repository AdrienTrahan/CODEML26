import pytest
import json
from pathlib import Path
import sys
from pydantic import ValidationError

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from validate import validate, validate_records, Record, Armature

def test_valid_record():
    data = {
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
    rec = Record.model_validate(data)
    assert rec.id == "CLP_S-100_p4_0001"
    assert rec.element == "TYPE C"
    assert rec.armature[0].diametre == "25M"

def test_invalid_record_rejected():
    # Invalid feuillet (does not match S-xxx)
    data = {
        "id": "CLP_INVALID_p4_0001",
        "source": "plan",
        "fichier": "L2C_PLAN_STR_CLP.pdf",
        "feuillet": "INVALID_SHEET",
        "page": 4,
        "x": 100.0,
        "y": 100.0,
        "type_element": "semelle",
        "element": "TEST",
        "armature": [{"raw": "9-25M"}]
    }
    with pytest.raises(ValidationError):
        Record.model_validate(data)

def test_validate_file(tmp_path):
    valid_data = [
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
            "armature": [{"raw": "9-25M", "diametre": "25M", "quantite": 9}]
        }
    ]
    json_file = tmp_path / "test_plan.json"
    json_file.write_text(json.dumps(valid_data), encoding="utf-8")
    
    validated = validate(json_file)
    assert len(validated) == 1
    assert validated[0].id == "CLP_S-100_p4_0001"

def test_validate_da_and_colonne():
    data = {
        "id": "S-500_C-12_da",
        "source": "da",
        "fichier": "CLP_COLONNES.pdf",
        "feuillet": "S-500",
        "page": 1,
        "x": 412.5,
        "y": 318.0,
        "type_element": "colonne",
        "element": "C-12",
        "armature": [
            {
                "raw": "8-25M",
                "repere": "C12-1",
                "diametre": "25M",
                "quantite": 8,
                "espacement_mm": None,
                "longueur_mm": 3600.0,
            }
        ],
    }
    rec = Record.model_validate(data)
    assert rec.source == "da"
    assert rec.type_element == "colonne"
    assert rec.armature[0].quantite == 8

