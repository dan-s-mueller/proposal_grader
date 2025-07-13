import io
from pathlib import Path
from typing import Tuple, Dict, Any

from pdfminer.high_level import extract_text
from pdfminer.pdfpage import PDFPage
from openpyxl import load_workbook


def extract_pdf(path: str) -> Tuple[str, Dict[str, Any]]:
    """Extract raw text and simple metadata from a PDF."""
    text = extract_text(path)
    page_count = 0
    with open(path, "rb") as f:
        for _ in PDFPage.get_pages(f):
            page_count += 1
    meta = {"page_count": page_count}
    return text, meta


def extract_budget_xlsx(path: str) -> Dict[str, Any]:
    wb = load_workbook(path, data_only=True)
    sheet = wb.active
    return {"taba": sheet["C21"].value or 0,
            "subcontract_total": sheet["C12"].value or 0,
            "total": sheet["C17"].value or 0}
