"""This script generates a multi-page PDF from a mock text file and uses the ChromaDiverse class to extract features and make predictions."""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

from classes.chromadiverse import ChromaDiverse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def read_mock_text_file(file_path: str) -> list[str]:
    """
    Reads the mock text file and splits it into pages using '###' as the delimiter.

    Args:
        file_path (str): Path to the mock text file.

    Returns:
        List[str]: List of page contents as strings.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    pages = [page.strip() for page in content.split("###") if page.strip()]
    return pages


def write_pdf(pages: list[str], output_path: str) -> None:
    """
    Writes the given pages to a multi-page PDF.

    Args:
        pages (List[str]): List of page contents.
        output_path (str): Path to save the generated PDF.
    """
    c = canvas.Canvas(output_path, pagesize=LETTER)
    width, height = LETTER
    margin = 75
    line_height = 11

    for page in pages:
        y = height - margin
        for line in page.splitlines():
            if y < margin:
                c.showPage()
                y = height - margin
            c.drawString(margin, y, line)
            y -= line_height
        c.showPage()
    c.save()


def extract_labels_from_mock_txt(file_path: str) -> list:
    """
    Extracts the label for each page from the mock text file.
    Returns a list of labels in order.
    """
    labels = []
    with open(file_path, "r", encoding="utf-8") as f:
        for block in f.read().split("###"):
            block = block.strip()
            if not block:
                continue
            for line in block.splitlines():
                if line.startswith("Label:"):
                    labels.append(line.replace("Label:", "").strip())
                    break
    return labels


def main() -> None:
    """
    Main function to read the mock text file and generate a multi-page PDF.
    """
    pdf_name = "mock_pdf.pdf"
    input_txt = Path("data/src/mock_pdf_data.txt")
    output_pdf = Path("data/pdf/mock_pdf.pdf")

    pages = read_mock_text_file(str(input_txt))
    write_pdf(pages, str(output_pdf))
    print(f"PDF generated at {output_pdf.resolve()}")
    chroma_diverse = ChromaDiverse()
    print("Loading models")
    chroma_diverse.load_all_models(
        program_model_path="notebooks/mlruns/0/6811a419a4c742afab4c8025874c1b0c/artifacts/model",
        company_model_path="notebooks/mlruns/0/e3024f8cced046cc8627814ba78c8b09/artifacts/model",
        donor_model_path="notebooks/mlruns/0/5270f1eeb9bf4e51957418692933b6e8/artifacts/model",
        offline=True,
    )
    tempFilePath = "data/pdf"
    chroma_diverse.pdf_name = pdf_name
    chroma_diverse.temp_blob_pdf = str(output_pdf)
    chroma_diverse.temp_pdf = tempFilePath + "/"
    chroma_diverse.temp_json = tempFilePath + "/" + pdf_name[:-4] + "_features.json"
    chroma_diverse.prediction_json = tempFilePath + "/" + pdf_name[:-4] + "_predictions.json"

    print("Extract Features")
    chroma_diverse.extract_features(skip_blob_write=True)

    print("---Classification---")
    labelled_features, labels = chroma_diverse.make_predictions(
        drop_program_features=["other", "stopword"], drop_company_features=[], drop_donor_features=["other", "stopword"], skip_blob_write=True
    )

    # Override labels with those from the mock text file
    correct_labels = extract_labels_from_mock_txt(str(input_txt))
    json_labelled_features = json.loads(labelled_features)
    for i, page in enumerate(json_labelled_features.get("features", [])):
        if i < len(correct_labels):
            page["label"] = correct_labels[i]

    with open("data/json/generated_mock_labelled.json", "w", encoding="utf-8") as f:
        json.dump(json_labelled_features, f, indent=4)

    # os.remove(chroma_diverse.temp_blob_pdf)
    # print(f"-----Labelling: Removed temp file: {chroma_diverse.temp_blob_pdf}-----")
    os.remove(chroma_diverse.temp_json)
    print(f"-----Labelling: Removed temp file: {chroma_diverse.temp_json}-----")
    os.remove(chroma_diverse.prediction_json)
    print(f"-----Labelling: Removed temp file: {chroma_diverse.prediction_json}-----")


if __name__ == "__main__":
    load_dotenv("classes/env_var_folder/.env")
    main()
