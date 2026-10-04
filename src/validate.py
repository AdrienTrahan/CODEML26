"""Validation des enregistrements JSON avec Pydantic."""
import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field

class Armature(BaseModel):
    raw: str
    repere: str | None = None
    diametre: str | None = Field(default=None, pattern=r"^[0-9]{2}M$")
    quantite: int | None = None
    espacement_mm: float | None = None
    longueur_mm: float | None = None
    bbox: list[float] | None = Field(default=None, min_length=4, max_length=4)

class Record(BaseModel):
    id: str
    source: Literal["plan", "da", "dessin_atelier"] = "plan"
    fichier: str
    feuillet: str = Field(pattern=r"^S-[0-9]{3}(\.[a-z0-9]+)?$")
    page: int
    x: float
    y: float
    type_element: Literal[
        "fondation",
        "radier",
        "semelle",
        "colonne",
        "poutre",
        "mur",
        "refend",
        "mur_cisaillement",
        "dalle",
    ]
    element: str
    armature: list[Armature]

def validate_records(records: list[dict]) -> list[Record]:
    """Validate a list of raw record dicts, returning list of validated Records."""
    return [Record.model_validate(record) for record in records]


def validate(path: Path) -> list[Record]:
    """Load JSON file, validate each record, return validated Records."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Root JSON must be a list of records")
    return validate_records(data)
