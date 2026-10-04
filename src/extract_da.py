"""Unified extraction adapter for Shop Drawings (Dessins d'Atelier, DA).

Extracts words from native vector text PDFs (PyMuPDF).
Rasterized pages can be handled via src/vlm_da.py instead.

Returns unified word dictionaries mapped to standard PDF points (1/72 in).
"""
import argparse
from collections.abc import Iterable
import json
from pathlib import Path
import sys

import pymupdf


def _page_words_vector(page: pymupdf.Page) -> list[dict]:
    """Extract words from native vector text."""
    keys = ("x0", "y0", "x1", "y1", "text", "block_no", "line_no", "word_no")
    return [dict(zip(keys, word)) for word in page.get_text("words")]


def extract_da_page(pdf_path: Path, page_1idx: int) -> list[dict]:
    """Extract words and bounding boxes from a DA page (vector text)."""
    pdf_path = Path(pdf_path)
    with pymupdf.open(pdf_path) as doc:
        if not 1 <= page_1idx <= len(doc):
            raise ValueError(f"Page {page_1idx} out of range [1, {len(doc)}]")
        return _page_words_vector(doc[page_1idx - 1])


def extract_da_pdf(pdf_path: Path, pages: Iterable[int] | None = None) -> list[dict]:
    """Extract words from selected pages (or all pages) of a shop drawing PDF."""
    pdf_path = Path(pdf_path)
    all_page_words = []
    with pymupdf.open(pdf_path) as doc:
        page_indices = range(1, len(doc) + 1) if pages is None else pages
        for p in page_indices:
            words = extract_da_page(pdf_path, p)
            all_page_words.append({
                "page": p,
                "words": words
            })
    return all_page_words


def _vlm_segment_records(segment: dict, fichier: str, feuillet: str, dpi: int = 125) -> list[dict]:
    """Convertit un segment ExtractedData (VLM) en records conformes à SCHEMA.json."""
    from src.parse import parse_armature_callout

    recs = []
    data = segment.get("data") or {}
    scale = dpi / 72.0
    for i, sm in enumerate(data.get("semelles", []), start=1):
        arms = []
        for value in (sm.get("data") or {}).values():
            arm = parse_armature_callout(str(value))
            arms.append(arm)
        recs.append(
            {
                "id": f"{Path(fichier).stem}_da_{feuillet}_p{segment['page']}_{i:04d}",
                "source": "da",
                "fichier": fichier,
                "feuillet": feuillet,
                "page": segment["page"],
                "x": round(segment["x"] / scale, 1),
                "y": round(segment["y"] / scale, 1),
                "type_element": "semelle",
                "element": sm.get("label", ""),
                "armature": arms,
            }
        )
    return recs


def extract_da_records(
    pdf_path: Path,
    feuillet: str,
    pages: Iterable[int] | None = None,
    config_path: str = "configs/config.yaml",
) -> list[dict]:
    """Extrait et structure les armatures d'un dessin d'atelier en records conformes à SCHEMA.json.

    Toutes les pages passent par le VLM local (src/vlm_da.py); aucun OCR.
    """
    from src.parse import parse_tokens
    from src.validate import validate_records

    pdf_path = Path(pdf_path)
    from src.validate import validate_records
    from src.vlm_da import extract_vlm_json

    pdf_path = Path(pdf_path)
    page_set = set(pages) if pages is not None else None
    records: list[dict] = []
    for seg in extract_vlm_json(pdf_path, config_path=config_path, pages=page_set):
        records.extend(_vlm_segment_records(seg, pdf_path.name, feuillet))
    validate_records(records)
    return records


def main():
    parser = argparse.ArgumentParser(description="Extraire les mots et coordonnées d'un dessin d'atelier (DA) PDF.")
    parser.add_argument("pdf", type=Path, help="Chemin du PDF DA")
    parser.add_argument("out", type=Path, help="Fichier JSON de sortie")
    parser.add_argument("--pages", type=int, nargs="+", help="Pages à extraire (toutes par défaut)")
    parser.add_argument("--records", action="store_true", help="Sortir des records SCHEMA.json via VLM (défaut: mots bruts vectoriels)")
    parser.add_argument("--feuillet", default="S-000", help="Feuillet à attribuer aux records (--records)")
    parser.add_argument("--config", default="configs/config.yaml")
    args = parser.parse_args()
    if args.records:
        records = extract_da_records(args.pdf, args.feuillet, pages=args.pages, config_path=args.config)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"{len(records)} éléments -> {args.out}")
        return
    extracted = extract_da_pdf(args.pdf, args.pages)
    total_words = sum(len(p["words"]) for p in extracted)
    
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(extracted, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Extrait {total_words} mots sur {len(extracted)} pages -> {args.out}")


if __name__ == "__main__":
    main()
