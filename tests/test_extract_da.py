import pytest
from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from extract_da import extract_da_page, extract_da_pdf

REPO_ROOT = Path(__file__).resolve().parent.parent
PDF_BASE_DIR = (
    REPO_ROOT / "l2c-participants"
    if (REPO_ROOT / "l2c-participants").exists()
    else REPO_ROOT / "l2c-participants (1)"
)


def test_extract_da_vector():
    """Test extraction on a vector DA PDF (CLP)."""
    pdf_path = PDF_BASE_DIR / "CLP" / "DA" / "Fondations" / "CLP_SEMELLES FND.pdf"
    if not pdf_path.exists():
        pytest.skip(f"File not found: {pdf_path}")
    words = extract_da_page(pdf_path, 1)
    assert len(words) > 1000
    # Words should have standard keys
    w = words[0]
    for key in ("x0", "y0", "x1", "y1", "text"):
        assert key in w
    assert any("COLONNE" in w["text"] for w in words)
