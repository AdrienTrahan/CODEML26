import pytest
from pathlib import Path
import sys

# Ensure src is importable
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from extract import extract_page

REPO_ROOT = Path(__file__).resolve().parent.parent
PDF_BASE_DIR = (
    REPO_ROOT / "l2c-participants"
    if (REPO_ROOT / "l2c-participants").exists()
    else REPO_ROOT / "l2c-participants (1)"
)
CLP_PDF = PDF_BASE_DIR / "CLP" / "L2C_PLAN_STR_CLP.pdf"

pytestmark = pytest.mark.skipif(not CLP_PDF.exists(), reason="CLP PDF not available")


def test_extract_page_clp_s100():
    # Page 4 in 1-based indexing
    words = extract_page(CLP_PDF, 4)
    assert isinstance(words, list)
    assert len(words) > 100
    
    # Check structure of word items
    first = words[0]
    for key in ("text", "x0", "y0", "x1", "y1", "block_no", "line_no"):
        assert key in first
        
    # Check that known text tokens from CLP S-100 are present
    texts = [w["text"] for w in words]
    assert "17-25M" in texts
    assert "9-25M" in texts
    assert "TYPE" in texts
    assert "ISOLÉES" in texts

