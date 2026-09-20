"""
PDF Document Text Extraction Service

Uses PyMuPDF to extract text from uploaded PDF documents.
"""

import fitz

from app.schemas.extraction_schema import ExtractedDocument, ExtractedField
from app.utils.file_utils import DOCUMENTS_DIR


def extract_document_data(document_id: str) -> ExtractedDocument | None:
    """
    Extract text from an uploaded PDF document using PyMuPDF.

    The uploaded file is located using its document_id prefix.
    """

    document_path = None

    if DOCUMENTS_DIR.exists():
        for file_path in DOCUMENTS_DIR.iterdir():
            if file_path.name.startswith(f"{document_id}_"):
                document_path = file_path
                break

    if document_path is None:
        return None

    # Currently support PDF text extraction.
    if document_path.suffix.lower() != ".pdf":
        return ExtractedDocument(
            document_id=document_id,
            fields=[],
        )

    try:
        pdf = fitz.open(document_path)

        extracted_text = []

        for page in pdf:
            text = page.get_text("text")
            if text.strip():
                extracted_text.append(text.strip())

        pdf.close()

        full_text = "\n".join(extracted_text)

    except Exception as exc:
        print(f"PDF extraction failed: {exc}")
        return None

    # For now, return the extracted text as a field.
    # Field-level mapping will be added next.
    fields = []

    if full_text.strip():
        fields.append(
            ExtractedField(
                field_name="document_text",
                value=full_text,
                source="pymupdf",
                confidence=1.0,
            )
        )

    return ExtractedDocument(
        document_id=document_id,
        fields=fields,
    )