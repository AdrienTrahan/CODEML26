"""Extraction du texte et des armatures d'un plan PDF."""
import argparse
from collections.abc import Iterable
import json
from pathlib import Path
import re

import pymupdf

from src.parse import parse_tokens
from src.validate import validate_records


# S-600A est normalisé en S-600.a pour respecter SCHEMA.json.
SHEET_PATTERN = re.compile(r"S-[0-9]{3}(?:\.[a-z0-9]+|[A-Z])?")


def _page_words(page: pymupdf.Page) -> list[dict]:
    keys = ("x0", "y0", "x1", "y1", "text", "block_no", "line_no", "word_no")
    return [dict(zip(keys, word)) for word in page.get_text("words")]


def extract_page(pdf: Path, page_1idx: int) -> list[dict]:
    """Retourne les mots et leurs coordonnées; les pages commencent à 1."""
    with pymupdf.open(pdf) as doc:
        if not 1 <= page_1idx <= len(doc):
            raise ValueError(f"Page {page_1idx} out of range [1, {len(doc)}]")
        return _page_words(doc[page_1idx - 1])


def detect_feuillet(words: list[dict]) -> str:
    """Prend le code écrit le plus grand (cartouche), puis le plus bas à droite."""
    candidates = [w for w in words if SHEET_PATTERN.search(w["text"])]
    if not candidates:
        return "S-000"
    best = max(candidates, key=lambda w: (w["y1"] - w["y0"], w["y0"], w["x0"]))
    sheet_m = SHEET_PATTERN.search(best["text"])
    sheet = sheet_m.group(0) if sheet_m else best["text"]
    if sheet[-1].isupper():
        sheet = f"{sheet[:-1]}.{sheet[-1].lower()}"
    return sheet


def extract_pdf(pdf: Path, pages: Iterable[int] | None = None) -> list[dict]:
    """Extrait et valide les armatures des pages choisies, ou du PDF entier."""
    pdf = Path(pdf)
    records = []
    with pymupdf.open(pdf) as doc:
        for page_number in range(1, len(doc) + 1) if pages is None else pages:
            if not 1 <= page_number <= len(doc):
                raise ValueError(f"Page {page_number} out of range [1, {len(doc)}]")
            page = doc[page_number - 1]
            words = _page_words(page)
            feuillet = detect_feuillet(words)
            records.extend(parse_tokens(words, pdf.name, feuillet, page_number))
    validate_records(records)
    return records


def main():
    parser = argparse.ArgumentParser(description="Extraire les armatures d'un plan PDF en JSON.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("out", type=Path, help="JSON à créer")
    parser.add_argument("--pages", type=int, nargs="+", help="Pages à extraire (toutes par défaut)")
    args = parser.parse_args()
    records = extract_pdf(args.pdf, args.pages)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{len(records)} éléments -> {args.out}")


if __name__ == "__main__":
    main()
