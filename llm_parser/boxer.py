import base64
from pathlib import Path

import pymupdf


class PDFBoxer:
    def __init__(
        self,
        dpi: int = 100,
        image_format: str = "jpg",
        jpg_quality: int = 60,
        gray: bool = True,
    ):
        self.dpi = dpi
        self.image_format = image_format
        self.jpg_quality = jpg_quality
        self.gray = gray

    def _merge_hits(self, rects, max_gap):
        rects = sorted(rects, key=lambda r: (round(r.y0), r.x0))
        merged = []
        for r in rects:
            if merged:
                last = merged[-1]
                same_line = min(last.y1, r.y1) - max(last.y0, r.y0) > 0.5 * min(last.height, r.height)
                if same_line and r.x0 - last.x1 <= max_gap:
                    merged[-1] = last | r
                    continue
            merged.append(r)
        return merged

    def _rect_to_base64(self, page, display_rect) -> str | None:
        clip = display_rect & page.rect
        if clip.is_empty:
            return None
        pix = page.get_pixmap(
            clip=clip,
            dpi=self.dpi,
            colorspace=pymupdf.csGRAY if self.gray else pymupdf.csRGB,
            alpha=False,
        )
        if pix.width == 0 or pix.height == 0:
            return None
        if self.image_format == "jpg":
            data = pix.tobytes("jpg", jpg_quality=self.jpg_quality)
        else:
            data = pix.tobytes("png")
        return base64.b64encode(data).decode("ascii")

    def box(
        self,
        pdf_path,
        criterion,
        out_path: str | None = "highlighted.pdf",
        file_name: str | None = None,
    ) -> list[dict]:
        doc = pymupdf.open(pdf_path)
        file_name = file_name or Path(pdf_path).name
        results = []

        for page in doc:
            to_display = page.rotation_matrix
            to_page = page.derotation_matrix

            hits = []
            for code in criterion.codes:
                hits += [r * to_display for r in page.search_for(code)]
            if not hits:
                continue

            avg_h = sum(r.height for r in hits) / len(hits)
            boxes = []
            for rect in self._merge_hits(hits, max_gap=avg_h):
                display_rect = criterion.get_box(criterion.codes[0], rect)
                if display_rect is None:
                    continue
                page_rect = display_rect * to_page
                boxes.append(page_rect)

                results.append({
                    "file_name": file_name,
                    "page_number": page.number + 1,
                    "text": page.get_text("text", clip=page_rect, sort=True).strip(),
                    "x": display_rect.x0,
                    "y": display_rect.y0,
                    "image": self._rect_to_base64(page, display_rect),
                })

            if out_path:
                for page_rect in boxes:
                    page.draw_rect(
                        page_rect,
                        color=(1, 0.8, 0),
                        fill=(1, 1, 0),
                        fill_opacity=0.35,
                        width=0.5,
                    )

        if out_path:
            doc.save(out_path)
        doc.close()
        return results