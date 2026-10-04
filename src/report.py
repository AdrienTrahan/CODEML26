"""Rapport PDF des armatures extraites pour un feuillet."""
import json
from pathlib import Path
from collections import Counter
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted, HRFlowable

def report(plan_json: Path, out_pdf: Path, da_json: Path | None = None) -> Path:
    """Generate a summary PDF report for an extracted plan JSON file."""
    with open(plan_json, "r", encoding="utf-8") as f:
        records = json.load(f)

    if da_json is None:
        candidate = Path(plan_json).parent / "da.json"
        da_json = candidate if candidate.exists() else None
    da_records = None
    if da_json is not None and Path(da_json).exists():
        with open(da_json, "r", encoding="utf-8") as f:
            da_records = json.load(f)
        
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out_pdf),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    heading2_style = styles["Heading2"]
    normal_style = styles["Normal"]
    
    elements = []
    
    # Header info
    fichier = escape(str(records[0].get("fichier", "N/A"))) if records else "N/A"
    feuillet = escape(str(records[0].get("feuillet", "N/A"))) if records else "N/A"
    page = records[0].get("page", "N/A") if records else "N/A"
    
    elements.append(Paragraph(f"Rapport d'Extraction Plan L2C - Feuillet {feuillet}", title_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>Fichier:</b> {fichier} | <b>Page:</b> {page} | <b>Total éléments extraits:</b> {len(records)}", normal_style))
    elements.append(Spacer(1, 16))
    
    # 1. Bar diameter breakdown
    dia_counter: Counter[str] = Counter()
    total_bars = 0
    for r in records:
        for a in r.get("armature", []):
            dia = a.get("diametre") or "Inconnu"
            qn = a.get("quantite")
            if qn is not None:
                dia_counter[dia] += qn
                total_bars += qn
            else:
                dia_counter[f"{dia} (annotations)"] += 1
            
    elements.append(Paragraph("1. Sommaire des Armatures par Diamètre", heading2_style))
    elements.append(Spacer(1, 6))
    
    dia_data = [["Diamètre", "Nombre total de barres"]]
    for dia, count in sorted(dia_counter.items()):
        dia_data.append([dia, str(count)])
    dia_data.append(["TOTAL", str(total_bars)])
    
    dia_table = Table(dia_data, colWidths=[200, 200])
    dia_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ECF0F1")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(dia_table)
    elements.append(Spacer(1, 20))
    
    # 2. Extracted Elements Sample Table
    elements.append(Paragraph("2. Détail des Éléments et Armatures Extraits", heading2_style))
    elements.append(Spacer(1, 6))
    
    detail_data = [["ID", "Élément", "Type", "Position (x, y)", "Armature(s)"]]
    for r in records:
        arms_desc = ", ".join(
            f"{a.get('raw', '')}" + (f" ({a.get('repere')})" if a.get('repere') else "")
            for a in r.get("armature", [])
        )
        pos = f"({r.get('x', 0):.1f}, {r.get('y', 0):.1f})"
        detail_data.append([
            r.get("id", ""),
            r.get("element", ""),
            r.get("type_element", ""),
            pos,
            arms_desc
        ])
        
    # Paragraph permet aux longues annotations de revenir à la ligne.
    cell_style = styles["BodyText"]
    cell_style.fontSize = 8
    cell_style.leading = 10
    header_style = styles["Heading5"]
    header_style.textColor = colors.whitesmoke
    header_style.fontSize = 8
    header_style.leading = 10
    detail_data = [
        [Paragraph(escape(str(value)), header_style if index == 0 else cell_style) for value in row]
        for index, row in enumerate(detail_data)
    ]
    detail_table = Table(detail_data, colWidths=[110, 80, 70, 90, 190], repeatRows=1)
    detail_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    elements.append(detail_table)
    elements.append(Spacer(1, 20))

    # 3. Detected JSON
    elements.append(Paragraph("3. JSON Détecté", heading2_style))
    elements.append(Spacer(1, 6))
    json_style = styles["Code"]
    json_style.fontSize = 6
    json_style.leading = 8

    def _dump(data: Any) -> None:
        json_text = json.dumps(data, indent=2, ensure_ascii=False)
        lines = escape(json_text).splitlines()
        for i in range(0, len(lines), 80):
            elements.append(Preformatted("\n".join(lines[i:i + 80]), json_style))

    elements.append(Paragraph("<b>Plan</b>", normal_style))
    elements.append(Spacer(1, 4))
    _dump(records)

    if da_records is not None:
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey, spaceBefore=4, spaceAfter=4))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("<b>DA (Dessins d'Atelier)</b>", normal_style))
        elements.append(Spacer(1, 4))
        _dump(da_records)

    doc.build(elements)
    return out_pdf


def audit_report(
    discrepancies: list[Any],
    out_pdf: Path,
    title: str = "Rapport d'Audit de Conformité (Plan L2C vs Dessins d'Atelier)",
    projet: str = "CLP"
) -> Path:
    """Generate an official civil engineering audit report PDF comparing Plan vs DA."""
    out_pdf = Path(out_pdf)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    
    doc = SimpleDocTemplate(
        str(out_pdf),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    title_style.fontSize = 16
    title_style.leading = 20

    heading2_style = styles["Heading2"]
    heading2_style.fontSize = 12
    heading2_style.leading = 15

    normal_style = styles["Normal"]
    normal_style.fontSize = 9
    normal_style.leading = 12

    elements = []

    # Title & Metadata
    elements.append(Paragraph(escape(title), title_style))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        f"<b>Projet:</b> {escape(projet)} | <b>Total éléments audités:</b> {len(discrepancies)}",
        normal_style
    ))
    elements.append(Spacer(1, 14))

    # Calculate summary metrics
    # discrepancies can be Discrepancy instances or dicts
    disc_dicts = [d.to_dict() if hasattr(d, "to_dict") else dict(d) for d in discrepancies]
    
    total_inspected = len(disc_dicts)
    total_conforme = sum(1 for d in disc_dicts if d.get("statut") == "CONFORME")
    total_non_conforme = total_inspected - total_conforme
    conformity_rate = (total_conforme / total_inspected * 100.0) if total_inspected else 0.0

    # 1. Executive Summary Table
    elements.append(Paragraph("1. Sommaire Exécutif de Conformité", heading2_style))
    elements.append(Spacer(1, 6))

    summary_data = [
        ["Indicateur", "Valeur", "Statut / Interprétation"],
        ["Éléments Inspectés", str(total_inspected), "Couverture complète du benchmark"],
        ["Éléments Conformes", str(total_conforme), f"{conformity_rate:.1f}% des éléments"],
        ["Écarts Détectés", str(total_non_conforme), "Nécessite vérification avant coulage" if total_non_conforme else "Aucune anomalie"],
        ["Niveau de Risque Global", "ÉLEVÉ" if total_non_conforme > 2 else ("MOYEN" if total_non_conforme else "NUL"), "Biais strict sécurité civile (Recall >> Precision)"],
    ]
    summary_table = Table(summary_data, colWidths=[150, 80, 310])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B4F72")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 14))

    # 2. Sheet breakdown table
    elements.append(Paragraph("2. Ventilation par Feuillet", heading2_style))
    elements.append(Spacer(1, 6))

    by_feuillet: dict[str, list[dict]] = {}
    for d in disc_dicts:
        by_feuillet.setdefault(d.get("feuillet", "S-000"), []).append(d)

    feuillet_data = [["Feuillet", "Éléments", "Conformes", "Non-Conformes", "Taux de conformité"]]
    for f_code, items in sorted(by_feuillet.items()):
        c_count = sum(1 for it in items if it.get("statut") == "CONFORME")
        nc_count = len(items) - c_count
        rate = (c_count / len(items) * 100.0) if items else 0.0
        feuillet_data.append([
            f_code,
            str(len(items)),
            str(c_count),
            str(nc_count),
            f"{rate:.0f}%"
        ])
    feuillet_table = Table(feuillet_data, colWidths=[100, 80, 80, 100, 180])
    feuillet_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(feuillet_table)
    elements.append(Spacer(1, 14))

    # 3. Detailed Discrepancies Table
    elements.append(Paragraph("3. Registre Détaillé de l'Audit (Conformités & Écarts)", heading2_style))
    elements.append(Spacer(1, 6))

    detail_data = [["Feuillet", "Localisation", "Plan L2C", "Dessin Atelier (DA)", "Statut", "Écart constaté (Delta)"]]
    for d in disc_dicts:
        detail_data.append([
            d.get("feuillet", ""),
            d.get("element", ""),
            d.get("plan_callout") or "—",
            d.get("da_callout") or "—",
            d.get("statut", ""),
            d.get("delta") or "Aucun écart (Conforme)"
        ])

    cell_style = styles["BodyText"]
    cell_style.fontSize = 7.5
    cell_style.leading = 9

    header_style = styles["Heading5"]
    header_style.textColor = colors.whitesmoke
    header_style.fontSize = 8
    header_style.leading = 10

    table_rows = []
    for r_idx, row in enumerate(detail_data):
        row_cells = []
        for c_idx, val in enumerate(row):
            if r_idx == 0:
                p = Paragraph(escape(str(val)), header_style)
            else:
                p = Paragraph(escape(str(val)), cell_style)
            row_cells.append(p)
        table_rows.append(row_cells)

    detail_table = Table(table_rows, colWidths=[55, 95, 95, 95, 95, 105], repeatRows=1)
    
    # Apply row-level background styles based on status
    t_styles = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BDC3C7")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]

    for idx, d in enumerate(disc_dicts, start=1):
        stat = d.get("statut", "")
        if stat == "CONFORME":
            bg = colors.HexColor("#EAFAF1")  # Validated / Approved light green
        elif stat in ("MANQUANT", "AJOUTÉ"):
            bg = colors.HexColor("#FEF9E7")  # Amber / Note for missing/added
        else:
            bg = colors.HexColor("#FDEDEC")  # Critical discrepancy red tint
        t_styles.append(("BACKGROUND", (0, idx), (-1, idx), bg))

    detail_table.setStyle(TableStyle(t_styles))
    elements.append(detail_table)

    doc.build(elements)
    return out_pdf

