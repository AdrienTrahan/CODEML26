


from pathlib import Path

from tqdm import tqdm

from llm_parser.boxer import PDFBoxer
from llm_parser.boxing_criterions import CRITERIONS
from llm_parser.model import ModelEvaluator
from llm_parser.ocr_pdf import OCRPdf
from utils.config import load_config

config = load_config("configs/config.yaml")

evaluator = ModelEvaluator(
    config["fondations"]["model"]["model_name"],
    config["fondations"]["model"]["base_url"],
    config["fondations"]["model"]["api_key"],
    config["fondations"]["model"]["max_tokens"],
)

ocr_pdf = OCRPdf()
boxer = PDFBoxer()


def find_objects_in_pdf(pdf_path, criterion):
    original_file_name = Path(pdf_path).name
    text_pdf = ocr_pdf.get_textual_pdf(pdf_path)
    boxes = boxer.box(text_pdf, criterion)
    objects = []
    for box in tqdm(boxes):
        object = evaluator.evaluate(
            config["fondations"]["model"]["prompt"],
            criterion.schema,
            box["image"],
            None
        )
        if object is None:
            continue
        objects.append({
            "id": object.id,
            "source": "da",
            "fichier": original_file_name,
            "feuillet": criterion.series_type.value,
            "page": box["page_number"],
            "x": box["x"],
            "y": box["y"],
            "type_element": criterion.object_type.value,
            "data": object.data
        })
    return objects

def find_all_objects_in_pdf(pdf_path):
    all_objects = []
    for criterion in CRITERIONS:
        found_object = find_objects_in_pdf(pdf_path, criterion)
        if found_object:
            all_objects.extend(found_object)
    return all_objects

def find_all_objects_in_all_pdfs(pdf_paths):
    all_objects = []
    for pdf_path in tqdm(pdf_paths):
        all_objects.extend(find_all_objects_in_pdf(pdf_path))
    return all_objects