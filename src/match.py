"""Moteur de comparaison et de détection des non-conformités (Matching & Discrepancy Engine).

Compare les armatures extraites du Plan structurel (L2C) avec celles des Dessins d'Atelier (DA).
Philosophie de décision: Biais strict vers les faux positifs pour garantir la sécurité civile
(Recall >> Precision).
"""
import argparse
from dataclasses import asdict, dataclass
from enum import StrEnum
import json
from pathlib import Path
import re
from typing import Any

from rapidfuzz import fuzz

from src.parse import canonicalize_grid


class Classification(StrEnum):
    CONFORME = "CONFORME"
    NON_CONFORME_QUANTITE = "NON-CONFORME QUANTITÉ"
    NON_CONFORME_DIAMETRE = "NON-CONFORME DIAMÈTRE"
    NON_CONFORME_ESPACEMENT = "NON-CONFORME ESPACEMENT"
    NON_CONFORME_NOTATION = "NON-CONFORME NOTATION"
    MANQUANT = "MANQUANT"
    AJOUTE = "AJOUTÉ"


@dataclass
class Discrepancy:
    feuillet: str
    element: str
    type_element: str
    statut: Classification
    delta: str | None
    plan_callout: str | None
    da_callout: str | None
    confidence: float
    plan_id: str | None = None
    da_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["statut"] = str(self.statut)
        return d


def _format_arms(arms: list[dict]) -> str:
    """Format a list of armature dicts into a concise summary string."""
    if not arms:
        return "N/A"
    return " / ".join(a.get("raw") or f"{a.get('quantite')}-{a.get('diametre')}" for a in arms)


def _is_parens_notation(arm: dict) -> bool:
    """Check if armature was defined using parens notation like 16(8)."""
    raw = arm.get("raw", "")
    repere = arm.get("repere") or ""
    return bool(re.search(r"\(\d+\)", raw) or re.search(r"^\(\d+\)$", repere))


def _align_armature_pairs(plan_arms: list[dict], da_arms: list[dict]) -> list[tuple[dict | None, dict | None]]:
    """Align armature callouts between plan and DA by matching diameter or role."""
    if len(plan_arms) <= 1 and len(da_arms) <= 1:
        p = plan_arms[0] if plan_arms else None
        d = da_arms[0] if da_arms else None
        return [(p, d)]

    pairs = []
    unmatched_da = list(da_arms)
    for p in plan_arms:
        best_d = None
        # Priority 1: Match by exact diameter
        for d in unmatched_da:
            if p.get("diametre") and d.get("diametre") and p["diametre"] == d["diametre"]:
                best_d = d
                break
        # Priority 2: Match by role (both have spacing / ties)
        if best_d is None:
            p_esp = p.get("espacement_mm") is not None
            for d in unmatched_da:
                d_esp = d.get("espacement_mm") is not None
                if p_esp == d_esp:
                    best_d = d
                    break
        if best_d is not None:
            pairs.append((p, best_d))
            unmatched_da.remove(best_d)
        elif unmatched_da:
            pairs.append((p, unmatched_da.pop(0)))
        else:
            pairs.append((p, None))
    for d in unmatched_da:
        pairs.append((None, d))
    return pairs


def compare_armatures(plan_arms: list[dict], da_arms: list[dict]) -> tuple[Classification, str | None]:
    """Compare armatures of a linked element and determine classification and delta description."""
    if plan_arms and not da_arms:
        return Classification.MANQUANT, "Armature absente du dessin d'atelier (DA)"
    if da_arms and not plan_arms:
        return Classification.AJOUTE, "Armature ajoutée au DA (non spécifiée au plan)"
    if not plan_arms and not da_arms:
        return Classification.CONFORME, None

    # Check each aligned pair of armatures
    pairs = _align_armature_pairs(plan_arms, da_arms)
    for plan_arm, da_arm in pairs:
        if plan_arm is None and da_arm is not None:
            return Classification.AJOUTE, f"Armature supplémentaire dans DA: {da_arm.get('raw')}"
        if da_arm is None and plan_arm is not None:
            return Classification.MANQUANT, f"Armature manquante dans DA: {plan_arm.get('raw')}"

        assert plan_arm is not None and da_arm is not None
        plan_raw = plan_arm.get("raw", "")
        da_raw = da_arm.get("raw", "")

        # 1. Check parens notation discrepancy (e.g. 16(8) vs 20(8))
        if _is_parens_notation(plan_arm) or _is_parens_notation(da_arm):
            plan_qn = plan_arm.get("quantite")
            da_qn = da_arm.get("quantite")
            if plan_qn != da_qn or plan_raw != da_raw:
                return (
                    Classification.NON_CONFORME_NOTATION,
                    f"Notation modifiée: {plan_raw} -> {da_raw}",
                )

        # 2. Check diameter discrepancy (Civil safety critical)
        plan_dia = plan_arm.get("diametre")
        da_dia = da_arm.get("diametre")
        if plan_dia and da_dia and plan_dia != da_dia:
            return (
                Classification.NON_CONFORME_DIAMETRE,
                f"Diamètre non-conforme: {plan_dia} -> {da_dia}",
            )
        elif (plan_dia and not da_dia) or (da_dia and not plan_dia):
            return (
                Classification.NON_CONFORME_NOTATION,
                f"Spécification divergente: {plan_raw} (Plan) vs {da_raw} (DA)",
            )

        # 3. Check quantity discrepancy
        plan_qn = plan_arm.get("quantite")
        da_qn = da_arm.get("quantite")
        if plan_qn is not None and da_qn is not None and plan_qn != da_qn:
            diff = da_qn - plan_qn
            sign = f"+{diff}" if diff > 0 else f"{diff}"
            return (
                Classification.NON_CONFORME_QUANTITE,
                f"{sign} barres ({plan_qn} -> {da_qn})",
            )

        # 4. Check spacing discrepancy
        plan_esp = plan_arm.get("espacement_mm")
        da_esp = da_arm.get("espacement_mm")
        if plan_esp is not None and da_esp is not None:
            if abs(plan_esp - da_esp) > 5.0:  # Tolerance of 5mm (~0.2 in)
                plan_in = round(plan_esp / 25.4)
                da_in = round(da_esp / 25.4)
                return (
                    Classification.NON_CONFORME_ESPACEMENT,
                    f"Espacement non-conforme: {plan_in}\" -> {da_in}\" ({plan_esp} mm -> {da_esp} mm)",
                )

        # 5. Check callout structure mismatch (e.g. spacing specified in one, count in the other)
        if (plan_esp is not None and da_qn is not None and da_esp is None) or (
            plan_qn is not None and da_esp is not None and da_qn is None
        ):
            return (
                Classification.NON_CONFORME_NOTATION,
                f"Spécification divergente: {plan_raw} (Plan) vs {da_raw} (DA)",
            )

    return Classification.CONFORME, None


def _clean_key(name: str) -> str:
    """Normalize element name for fuzzy entity linking."""
    norm = canonicalize_grid(name)
    norm = re.sub(r"\b(ÉLÉVATION|ELEVATION)\b", "ELEV", norm, flags=re.I)
    norm = re.sub(r"\s+", " ", norm).strip().upper()
    # "TYPE A" (plan) and "A-11" / "A 11" (DA) denote the same element family.
    m = re.fullmatch(r"TYPE\s+([A-Z])", norm)
    if m:
        return f"TYPE {m.group(1)}"
    m = re.fullmatch(r"([A-Z])\s*[-–]\s*.+", norm)
    if m:
        return f"TYPE {m.group(1)}"
    m = re.fullmatch(r"([A-Z])\d+", norm)
    if m:
        return f"TYPE {m.group(1)}"
    return norm


def match_elements(
    plan_records: list[dict],
    da_records: list[dict],
    threshold: float = 70.0,
    as_dicts: bool = False,
) -> list[Any]:
    """Link elements between Plan and DA and classify discrepancies.
    
    Returns a list of Discrepancy instances (or dicts if as_dicts=True).
    """
    discrepancies: list[Discrepancy] = []

    # Partition records by feuillet
    plan_by_feuillet: dict[str, list[dict]] = {}
    for p in plan_records:
        plan_by_feuillet.setdefault(p.get("feuillet", "S-000"), []).append(p)

    da_by_feuillet: dict[str, list[dict]] = {}
    for d in da_records:
        da_by_feuillet.setdefault(d.get("feuillet", "S-000"), []).append(d)

    all_feuillets = sorted(set(plan_by_feuillet.keys()) | set(da_by_feuillet.keys()))

    for feuillet in all_feuillets:
        p_list = plan_by_feuillet.get(feuillet, [])
        d_list = da_by_feuillet.get(feuillet, [])

        matched_da_ids: set[str] = set()

        for p_rec in p_list:
            p_elem = p_rec.get("element", "")
            p_clean = _clean_key(p_elem)
            p_arms = p_rec.get("armature", [])
            p_type = p_rec.get("type_element", "fondation")

            # Find candidate in DA
            best_da = None
            best_score = 0.0

            for d_rec in d_list:
                if d_rec.get("id") in matched_da_ids:
                    continue
                d_elem = d_rec.get("element", "")
                d_clean = _clean_key(d_elem)

                # Direct exact match
                if p_clean == d_clean:
                    score = 100.0
                elif p_clean.startswith("TYPE ") and d_clean.startswith("TYPE "):
                    score = 0.0
                else:
                    # Token sort ratio & partial ratio
                    score = max(
                        float(fuzz.token_sort_ratio(p_clean, d_clean)),
                        float(fuzz.partial_ratio(p_clean, d_clean)),
                    )

                if score > best_score:
                    best_score = score
                    best_da = d_rec

            if best_da is not None and best_score >= threshold:
                da_id = str(best_da.get("id", ""))
                if da_id:
                    matched_da_ids.add(da_id)
                d_arms = best_da.get("armature", [])
                statut, delta = compare_armatures(p_arms, d_arms)
                discrepancies.append(
                    Discrepancy(
                        feuillet=feuillet,
                        element=p_elem,
                        type_element=p_type,
                        statut=statut,
                        delta=delta,
                        plan_callout=_format_arms(p_arms),
                        da_callout=_format_arms(d_arms),
                        confidence=round(best_score / 100.0, 2),
                        plan_id=p_rec.get("id"),
                        da_id=best_da.get("id"),
                    )
                )
            else:
                # Missing in DA
                discrepancies.append(
                    Discrepancy(
                        feuillet=feuillet,
                        element=p_elem,
                        type_element=p_type,
                        statut=Classification.MANQUANT,
                        delta="Élément présent au plan mais absent du DA",
                        plan_callout=_format_arms(p_arms),
                        da_callout=None,
                        confidence=1.0,
                        plan_id=p_rec.get("id"),
                        da_id=None,
                    )
                )

        # Added elements in DA with no counterpart in Plan
        for d_rec in d_list:
            if d_rec.get("id") not in matched_da_ids:
                d_arms = d_rec.get("armature", [])
                discrepancies.append(
                    Discrepancy(
                        feuillet=feuillet,
                        element=d_rec.get("element", ""),
                        type_element=d_rec.get("type_element", "fondation"),
                        statut=Classification.AJOUTE,
                        delta="Élément présent au DA mais absent du plan",
                        plan_callout=None,
                        da_callout=_format_arms(d_arms),
                        confidence=1.0,
                        plan_id=None,
                        da_id=d_rec.get("id"),
                    )
                )

    if as_dicts:
        return [d.to_dict() for d in discrepancies]
    return discrepancies


def main():
    parser = argparse.ArgumentParser(description="Comparer les armatures Plan vs DA et générer un rapport d'audit.")
    parser.add_argument("plan", type=Path, help="Fichier JSON des éléments extraits du Plan")
    parser.add_argument("da", type=Path, help="Fichier JSON des éléments extraits des DA")
    parser.add_argument("--out", type=Path, default=Path("out/discrepancies.json"), help="Fichier JSON de sortie des écarts")
    parser.add_argument("--pdf", type=Path, help="Rapport PDF d'audit à générer (optionnel)")
    parser.add_argument("--threshold", type=float, default=70.0, help="Seuil de similarité fuzzy matching (70.0 par défaut)")
    args = parser.parse_args()

    with open(args.plan, "r", encoding="utf-8") as f:
        plan_records = json.load(f)
    with open(args.da, "r", encoding="utf-8") as f:
        da_records = json.load(f)

    discrepancies = match_elements(plan_records, da_records, threshold=args.threshold)
    disc_dicts = [d.to_dict() for d in discrepancies]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(disc_dicts, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Audit terminé: {len(discrepancies)} éléments analysés -> {args.out}")

    if args.pdf:
        from src.report import audit_report
        audit_report(discrepancies, args.pdf)
        print(f"Rapport d'audit PDF généré -> {args.pdf}")


if __name__ == "__main__":
    main()

