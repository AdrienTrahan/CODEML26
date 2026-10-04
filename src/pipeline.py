"""Pipeline E2E: Plan L2C -> extraction -> extraction DA (object finder) -> audit -> rapport PDF."""
import argparse
import json
import re
from pathlib import Path

import pymupdf

from llm_parser.object_finder import find_all_objects_in_pdf
from src.extract import extract_pdf
from src.match import match_elements
from src.report import audit_report

SHEET_RE = re.compile(r"S-\d{3}[A-Za-z]?")


def run(
    plan_pdf: Path,
    da_paths: list[Path],
    out_dir: Path,
    pages: list[int] | None = None,
    feuillet: str | None = None,
    projet: str = "CLP",
) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    plan_records = extract_pdf(Path(plan_pdf), pages=pages)
    plan_json = out_dir / "plan.json"
    plan_json.write_text(json.dumps(plan_records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Plan: {len(plan_records)} éléments -> {plan_json}")

    da_records: list[dict] = []
    for da_pdf in da_paths:
        recs = find_all_objects_in_pdf(Path(da_pdf))
        da_records.extend(recs)
        print(f"DA {da_pdf.name}: {len(recs)} éléments")
    da_json = out_dir / "da.json"
    da_json.write_text(json.dumps(da_records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"DA total: {len(da_records)} éléments -> {da_json}")

    discrepancies = match_elements(plan_records, da_records)
    disc_json = out_dir / "discrepancies.json"
    disc_json.write_text(
        json.dumps([d.to_dict() for d in discrepancies], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Audit: {len(discrepancies)} éléments -> {disc_json}")

    audit_pdf = out_dir / "audit.pdf"
    audit_report(discrepancies, audit_pdf, projet=projet)
    print(f"Rapport: {audit_pdf}")
    return {"plan": len(plan_records), "da": len(da_records), "discrepancies": len(discrepancies)}


def main():
    parser = argparse.ArgumentParser(description="Pipeline E2E Plan vs DA (object finder pour les DA).")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--da", type=Path, nargs="+", required=True, help="PDF(s) DA ou dossier(s) de DA")
    parser.add_argument("--out", type=Path, default=Path("out/e2e"))
    parser.add_argument("--pages", type=int, nargs="+", help="Pages du plan à extraire")
    parser.add_argument("--feuillet", help="Feuillet à forcer pour tous les DA (sinon détecté)")
    parser.add_argument("--projet", default="CLP")
    args = parser.parse_args()

    da_paths: list[Path] = []
    for p in args.da:
        if p.is_dir():
            da_paths.extend(sorted(p.rglob("*.pdf")))
        else:
            da_paths.append(p)
    if not da_paths:
        raise SystemExit("Aucun PDF DA trouvé")

    run(args.plan, da_paths, args.out, pages=args.pages, feuillet=args.feuillet, projet=args.projet)


if __name__ == "__main__":
    main()
