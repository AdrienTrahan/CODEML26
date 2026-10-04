"""Lecture des annotations d'armature et association aux éléments du plan."""
import re
from pathlib import Path

IN_MM = 25.4
FT_MM = 304.8

def get_bbox(words: list[dict]) -> list[float]:
    """Compute bounding box [x0, y0, x1, y1] for a list of word dictionaries."""
    if not words:
        return [0.0, 0.0, 0.0, 0.0]
    return [
        round(min(w["x0"] for w in words), 1),
        round(min(w["y0"] for w in words), 1),
        round(max(w["x1"] for w in words), 1),
        round(max(w["y1"] for w in words), 1),
    ]

PAT_QN_DIAM = re.compile(
    r"(?:(?P<rep>ARM\.?|VERT\.?|LONG\.?|TRANS\.?|LIG\.?|ÉTR\.?|ETR\.?|ÉTRI\.?|ETRI\.?|EN ATTENTE|ATT\.?|GOUJ\.?)\s*:?\s*)?"
    r"(?:(?P<mult>\d+)\s*[x×]\s*)?"
    r"(?P<qn>\d+)\s*[-–x× ]\s*"
    r"(?P<dia>\d{2}M)"
    r"(?:\s+[0-9A-Z-]+)?"
    r"(?:\s*@\s*(?P<esp>\d+(?:\.\d+)?)\s*(?:\"|''|in|po)?(?:\s*c/c)?)?",
    re.I,
)
PAT_AT = re.compile(
    r"(?:(?P<rep>LIG\.?|TRANS\.?|ÉTR\.?|RANG\s*\d+|1er\s*RANG|2e\s*RANG|H\.?|V\.?)\s*:?\s*)?(?P<dia>\d{2}M)\s*@\s*(?P<esp>\d+(?:\.\d+)?)\s*(?:\"|''|in|po)?(?:\s*c/c)?",
    re.I,
)
PAT_PARENS = re.compile(r"(?P<qn>\d+)\s*\(\s*(?P<sub_qn>\d+)\s*\)")
PAT_IMPERIAL = re.compile(r"(?:(?P<ft>\d+)\s*['’])?\s*-?\s*(?P<in>\d+(?:\.\d+)?)\s*[\"”']")
PAT_RANG = re.compile(r"(?:1er|2e)\s*RANG|RANG\s*\d+", re.I)

def parse_length_mm(text: str) -> float | None:
    """Parse imperial notation like 15'-10", 2' - 8", 16" into millimeters.
    
    Returns rounded float in mm or None.
    """
    match = PAT_IMPERIAL.search(text.strip())
    if not match:
        return None
    return round(float(match.group("ft") or 0) * FT_MM + float(match.group("in")) * IN_MM, 1)


def get_modifiers(text: str) -> list[str]:
    """Repères communs à toutes les armatures d'un bloc."""
    modifiers = ["TOUT AUTOUR"] if "TOUT AUTOUR" in text.upper() else []
    rang = PAT_RANG.search(text)
    if rang:
        modifiers.append(rang.group().upper())
    return modifiers


def parse_armature_callout(
    text: str,
    repere: str | None = None,
    bbox: list[float] | None = None
) -> dict:
    """Parse a single text callout into an Armature dict.
    
    Handles QN-DIAM (17-25M), DIAM@ESP (15M@16" c/c), variants, and modifiers.
    """
    clean_text = text.strip()
    quantite: int | None = None
    diametre: str | None = None
    espacement_mm: float | None = None
    longueur_mm: float | None = None
    
    repere_parts = [repere] if repere else []
    for modifier in get_modifiers(clean_text):
        if modifier not in repere_parts:
            repere_parts.append(modifier)
    final_repere = " - ".join(repere_parts) or None

    # Match patterns
    m_qn = PAT_QN_DIAM.search(clean_text)
    m_at = PAT_AT.search(clean_text)
    m_parens = PAT_PARENS.search(clean_text)
    
    if m_qn:
        mult = int(m_qn.group("mult")) if m_qn.group("mult") else 1
        quantite = int(m_qn.group("qn")) * mult if m_qn.group("qn") else None
        diametre = m_qn.group("dia").upper()
        if m_qn.group("esp"):
            espacement_mm = round(float(m_qn.group("esp")) * IN_MM, 1)
        if not final_repere and m_qn.group("rep"):
            final_repere = m_qn.group("rep").upper()
    elif m_at:
        diametre = m_at.group("dia").upper()
        esp_val = float(m_at.group("esp"))
        espacement_mm = round(esp_val * IN_MM, 1)
        if not final_repere and m_at.group("rep"):
            final_repere = m_at.group("rep").upper()
    elif m_parens:
        quantite = int(m_parens.group("qn"))
        if not final_repere:
            final_repere = f"({m_parens.group('sub_qn')})"
    else:
        naked_dia = re.search(r"\b(\d{2}M)\b", clean_text)
        if naked_dia:
            diametre = naked_dia.group(1).upper()
            
    res: dict = {
        "raw": clean_text,
        "repere": final_repere,
        "diametre": diametre,
        "quantite": quantite,
        "espacement_mm": espacement_mm,
        "longueur_mm": longueur_mm,
    }
    if bbox is not None:
        res["bbox"] = [round(float(c), 1) for c in bbox]
    return res

def parse_all_armatures_from_text(text: str, bbox: list[float] | None = None) -> list[dict]:
    """Extract all distinct armature entries from a block or composite text."""
    clean_text = text.strip()
    modifiers = get_modifiers(clean_text)
    matches = list(PAT_QN_DIAM.finditer(clean_text)) + list(PAT_AT.finditer(clean_text))
    if not matches:
        matches = list(PAT_PARENS.finditer(clean_text))

    arms = []
    for match in matches:
        groups = match.groupdict()
        repere_parts = list(modifiers)
        if groups.get("rep"):
            repere_parts.insert(0, groups["rep"].upper())
        if groups.get("sub_qn"):
            repere_parts.append(f"({groups['sub_qn']})")
        
        qn = None
        if groups.get("qn"):
            mult = int(groups.get("mult") or 1)
            qn = int(groups["qn"]) * mult
            
        arms.append({
            "raw": match.group(),
            "repere": " - ".join(repere_parts) or None,
            "diametre": groups["dia"].upper() if groups.get("dia") else None,
            "quantite": qn,
            "espacement_mm": round(float(groups["esp"]) * IN_MM, 1) if groups.get("esp") else None,
            "longueur_mm": None,
            "bbox": bbox,
        })
    return arms


def get_grid_axes(words: list[dict]) -> tuple[list[tuple[float, str]], list[tuple[float, str]]]:
    """Extract horizontal and vertical grid coordinate axes from margin areas."""
    x_axes: list[tuple[float, str]] = []
    y_axes: list[tuple[float, str]] = []
    
    for w in words:
        txt = w["text"].strip()
        # Numbered axis along top/bottom margins
        if re.fullmatch(r"[0-9]{1,2}(?:\.[0-9]+)?", txt):
            if w["y0"] < 400 or w["y0"] > 2200:
                mid_x = (w["x0"] + w["x1"]) / 2
                x_axes.append((mid_x, txt))
        # Lettered axis along left/right margins
        elif len(txt) == 1 and "A" <= txt <= "Z":
            if w["x0"] < 450 or w["x0"] > 2900:
                mid_y = (w["y0"] + w["y1"]) / 2
                y_axes.append((mid_y, txt))
                
    return x_axes, y_axes

def canonicalize_grid(grid: str) -> str:
    """Normalize grid references like 'B/1.8', 'B-1.8', 'B 1.8' to 'B-1.8'."""
    clean = re.sub(r"[\s/–_]+", "-", grid.upper().strip()).rstrip("-")
    return clean


def find_nearest_grid(
    x: float,
    y: float,
    x_axes: list[tuple[float, str]],
    y_axes: list[tuple[float, str]]
) -> str | None:
    """Find closest grid intersection string like L-13 or K-6.5."""
    best_x = min(x_axes, key=lambda a: abs(a[0] - x))[1] if x_axes else None
    best_y = min(y_axes, key=lambda a: abs(a[0] - y))[1] if y_axes else None
    if best_x and best_y:
        return f"{best_y}-{best_x}"
    return best_x or best_y

def infer_type_element(text: str, feuillet: str) -> str:
    """Infer the structural type_element from block text or sheet series."""
    upper = text.upper()
    if any(k in upper for k in ["COLONNE", "COL."]):
        return "colonne"
    if any(k in upper for k in ["REFEND", "CISAILLEMENT", "ÉLÉVATION", "ELEVATION", "CA."]):
        return "refend"
    if "POUTRE" in upper:
        return "poutre"
    if "DALLE" in upper:
        return "dalle"
    if "RADIER" in upper:
        return "radier"
    if any(k in upper for k in ["SEMELLE", "EMPATTEMENT"]):
        return "semelle"
        
    # Fallback from feuillet number prefix
    if feuillet.startswith("S-5"):
        return "colonne"
    if feuillet.startswith("S-4"):
        return "refend"
    if feuillet.startswith("S-6"):
        return "dalle"
    if feuillet.startswith("S-3"):
        return "poutre"
    if feuillet.startswith("S-1") or feuillet.startswith("S-0"):
        return "semelle"
    return "fondation"

def parse_tokens(
    words: list[dict],
    fichier: str,
    feuillet: str,
    page: int
) -> list[dict]:
    """Parse extracted words into PlanArmature records conforming to SCHEMA.json."""
    records: list[dict] = []
    stem = Path(fichier).stem
    counter = 1
    
    x_axes, y_axes = get_grid_axes(words)
    consumed_coords: set[tuple[float, float]] = set()
    
    # 1. Parse NOMENCLATURE DES SEMELLES ISOLÉES Table (Foundation schedule)
    type_words = [w for w in words if re.match(r"^[TI1l|]YPE?$", w["text"], re.I) and 2650 <= w["x0"] <= 2800]
    for tw in type_words:
        row_words = [w for w in words if abs(w["y0"] - tw["y0"]) < 6 and 2650 <= w["x0"] <= 3150]
        row_words.sort(key=lambda x: x["x0"])
        row_text = " ".join(w["text"] for w in row_words)
        
        split_parts = re.split(r"[TI1l|]YPE?", row_text, maxsplit=1, flags=re.I)
        letter = split_parts[1].lstrip()[:1] if len(split_parts) > 1 else ""
        if not letter or not "A" <= letter <= "Z":
            continue
        element_name = f"TYPE {letter}"

        for w in row_words:
            consumed_coords.add((round(w["x0"], 1), round(w["y0"], 1)))
            
        arm_long_words = [w for w in row_words if 2960 <= w["x0"] <= 3025]
        arm_trans_words = [w for w in row_words if 3025 < w["x0"] <= 3090]
        longueur_words = [w for w in row_words if 2790 <= w["x0"] <= 2845]
        largeur_words = [w for w in row_words if 2850 <= w["x0"] <= 2905]
        
        longueur_txt = " ".join(w["text"] for w in longueur_words)
        largeur_txt = " ".join(w["text"] for w in largeur_words)
        longueur_mm = parse_length_mm(longueur_txt)
        largeur_mm = parse_length_mm(largeur_txt)
        
        armatures = []
        for arm_words, repere, length in (
            (arm_long_words, "ARM. LONG.", longueur_mm),
            (arm_trans_words, "ARM. TRANS.", largeur_mm),
        ):
            if arm_words:
                armature = parse_armature_callout(
                    " ".join(w["text"] for w in arm_words), repere, get_bbox(arm_words)
                )
                armature["longueur_mm"] = length
                armatures.append(armature)

        valid_armatures = [
            a for a in armatures
            if a.get("diametre") or a.get("quantite") is not None or a.get("espacement_mm") is not None
        ]
        
        if valid_armatures:
            records.append({
                "id": f"{stem}_{feuillet}_p{page}_{counter:04d}",
                "source": "plan",
                "fichier": fichier,
                "feuillet": feuillet,
                "page": page,
                "x": round(float((tw["x0"] + row_words[-1]["x1"]) / 2), 1),
                "y": round(float((tw["y0"] + tw["y1"]) / 2), 1),
                "type_element": "semelle",
                "element": element_name,
                "armature": valid_armatures,
            })
            counter += 1

    # 2. Parse Block-level and Line-level Callouts & Matrix Schedules
    # Group words by block_no
    blocks: dict[int, list[dict]] = {}
    for w in words:
        if (round(w["x0"], 1), round(w["y0"], 1)) in consumed_coords:
            continue
        if feuillet.startswith("S-1") and w["x0"] >= 2650 and w["y0"] >= 2190:
            continue
        blocks.setdefault(w["block_no"], []).append(w)
        
    for _, bwords in sorted(blocks.items()):
        bwords.sort(key=lambda x: (x["y0"], x["x0"]))
        block_text = " ".join(w["text"] for w in bwords)
        
        # Check if block has any rebar callout
        bbox = get_bbox(bwords)
        armatures = parse_all_armatures_from_text(block_text, bbox=bbox)
        if not armatures:
            continue
            
        mid_x = (bwords[0]["x0"] + bwords[-1]["x1"]) / 2
        mid_y = (bwords[0]["y0"] + bwords[-1]["y1"]) / 2
        
        # Determine element type
        type_elem = infer_type_element(block_text, feuillet)
        
        # Determine element name (grid location, section label, or description)
        grid_loc = find_nearest_grid(mid_x, mid_y, x_axes, y_axes)
        
        element_name = grid_loc or "ANNOTATION"
        if "TOUT AUTOUR" in block_text.upper():
            element_name = "DETAIL TOUT AUTOUR"
        elif "ÉLÉVATION" in block_text.upper():
            elev_match = re.search(r"ÉLÉVATION\s+([A-Z0-9]+)", block_text, re.I)
            if elev_match:
                element_name = f"ÉLÉVATION {elev_match.group(1).upper()}"
        elif type_elem == "refend" and "CA." in block_text:
            ca_match = re.search(r"\bCA\.\s*\d+x\d+\b", block_text, re.I)
            ca_name = ca_match.group(0).upper() if ca_match else "REFEND"
            element_name = f"{grid_loc} ({ca_name})" if grid_loc else ca_name

        records.append({
            "id": f"{stem}_{feuillet}_p{page}_{counter:04d}",
            "source": "plan",
            "fichier": fichier,
            "feuillet": feuillet,
            "page": page,
            "x": round(float((bbox[0] + bbox[2]) / 2), 1),
            "y": round(float((bbox[1] + bbox[3]) / 2), 1),
            "type_element": type_elem,
            "element": element_name,
            "armature": armatures,
        })
        counter += 1

    return records
