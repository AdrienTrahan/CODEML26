"""VLM-based extraction for rasterized DA PDFs (no OCR).

Uses llm_parser.PDFSegmenter to tile pages into patches and
llm_parser.ModelEvaluator to ask a local OpenAI-compatible vision model
(LM Studio, e.g. qwen/qwen3-vl-4b) for ExtractedData per patch.
Output: a JSON list of per-segment dicts usable downstream.
"""
import argparse
import json
from collections.abc import Iterable
from pathlib import Path

from llm_parser.model import ModelEvaluator
from llm_parser.schema import ExtractedData
from llm_parser.segmentation import PDFSegmenter
from utils.config import load_config


def extract_vlm_json(
    pdf_path: Path,
    config_path: str = "configs/config.yaml",
    pages: Iterable[int] | None = None,
) -> list[dict]:
    config = load_config(config_path)
    m = config["fondations"]["model"]
    evaluator = ModelEvaluator(m["model_name"], m["base_url"], m["api_key"], int(m["max_tokens"]))
    seg = PDFSegmenter(
        patch_width=config["fondations"]["pdf"]["patch_width"],
        patch_height=config["fondations"]["pdf"]["patch_height"],
        padding_width=config["fondations"]["pdf"]["padding_width"],
        padding_height=config["fondations"]["pdf"]["padding_height"],
        dpi=config["fondations"]["pdf"]["dpi"],
    )
    results: list[dict] = []
    for segment in seg.segment_pdf(str(pdf_path)):
        if pages is not None and segment.page_number not in pages:
            continue
        data = evaluator.evaluate(m["prompt"], ExtractedData, segment.image, segment.extracted_text)
        results.append(
            {
                "pdf": segment.pdf_path,
                "page": segment.page_number,
                "x": segment.x,
                "y": segment.y,
                "width": segment.width,
                "height": segment.height,
                "extracted_text": segment.extracted_text,
                "data": data.model_dump() if hasattr(data, "model_dump") else data,
            }
        )
    return results


def main():
    parser = argparse.ArgumentParser(description="Extraire les semelles d'un PDF via VLM local.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--config", default="configs/config.yaml")
    args = parser.parse_args()

    results = extract_vlm_json(args.pdf, config_path=args.config)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{len(results)} segments -> {args.out}")


if __name__ == "__main__":
    main()
