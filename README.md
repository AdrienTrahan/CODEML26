# CODEML26 - L2C

Extraction des armatures depuis des plans PDF : texte et coordonnées avec PyMuPDF, parsing des annotations, validation Pydantic, export JSON, rapport PDF.

## Installation

Python 3.12/3.13 et [uv](https://docs.astral.sh/uv/) :

```bash
uv sync --dev
```

## Utilisation

1. Extraire les armatures d'un plan en JSON :

```bash
uv run python -m src.extract plan.pdf out/plan.json
```

Pour ne traiter que certaines pages (numérotation à partir de 1) :

```bash
uv run python -m src.extract plan.pdf out/plan.json --pages 4 14 18 26
```

2. Valider le JSON et générer le rapport PDF :

```bash
uv run python -c "
from pathlib import Path
from src.validate import validate
from src.report import report
validate(Path('out/plan.json'))
report(Path('out/plan.json'), Path('out/plan_rapport.pdf'))
"
```

3. Lancer les tests :

```bash
uv run pytest -q
```

Le notebook `pipeline.ipynb` montre le même flux étape par étape (extraction, validation, JSON, rapport). Il faut y indiquer le chemin de votre PDF dans la première cellule — le dossier `l2c-participants/` n'est pas requis.

Les tests qui dépendent du plan de démo CLP sont ignorés automatiquement si ce PDF n'est pas présent.

## Modules

- `src/extract.py` : mots et coordonnées, code de feuillet, extraction du PDF et CLI.
- `src/parse.py` : annotations `9-25M`, `15M@16"`, conversion vers millimètres.
- `src/validate.py` : modèles Pydantic basés sur `SCHEMA.json`.
- `src/report.py` : sommaire et détail des annotations en PDF.

## Limites

- Texte vectoriel uniquement (pas d'OCR). Positions du tableau des semelles et des axes adaptées au projet CLP.
- Le feuillet est le code `S-xxx` écrit le plus grand sur la page; `S-600A` devient `S-600.a`. Pages sans code `S-xxx` non prises en charge.
- Espacements en pouces; longueurs disponibles dans le tableau des semelles seulement.
- Quantités additionnées par annotation, pas un métré global.

Ne pas publier les PDF fournis ni les données extraites.
