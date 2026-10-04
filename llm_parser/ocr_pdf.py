import hashlib
import ocrmypdf
import tempfile
import os
from pypdf import PdfReader
from pathlib import Path


class OCRPdf:
    def __init__(self, cache_dir: str = ".ocr_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def _file_hash(self, pdf_path: str) -> str:
        h = hashlib.sha256()
        with open(pdf_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def get_textual_pdf(self, pdf_path: str) -> str:
        reader = PdfReader(pdf_path)
        has_text = any(page.extract_text().strip() for page in reader.pages)

        if has_text:
            return pdf_path

        file_hash = self._file_hash(pdf_path)
        cached_path = self.cache_dir / f"{file_hash}.pdf"

        if cached_path.exists():
            return str(cached_path)

        ocrmypdf.ocr(
            pdf_path,
            cached_path,
            optimize=1,
        )
        return str(cached_path)