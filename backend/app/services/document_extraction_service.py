"""
Local Mock Document Extraction Service
NOTE: This is a MOCK/LOCAL implementation for information extraction.
No real OCR, Textract, or AI is performed yet.
"""

from app.schemas.extraction_schema import ExtractedDocument, ExtractedField
from app.utils.file_utils import DOCUMENTS_DIR


def extract_document_data(document_id: str) -> ExtractedDocument | None:
    """
    Extracts mock information fields from an uploaded document.
    [MOCK/LOCAL EXTRACTION: Deterministic test data with source='local_mock']
    """
    # Verify the document was uploaded and exists in local temp storage
    doc_exists = False
    if DOCUMENTS_DIR.exists():
        for file_path in DOCUMENTS_DIR.iterdir():
            if file_path.name.startswith(f"{document_id}_"):
                doc_exists = True
                break

    if not doc_exists:
        return None

    # Deterministic mock extracted fields representing user data extracted from documents
    fields = [
        ExtractedField(
            field_name="full_name",
            value="Girisha Varshini",
            source="local_mock",
            confidence=0.95,
        ),
        ExtractedField(
            field_name="date_of_birth",
            value="2000-01-15",
            source="local_mock",
            confidence=0.92,
        ),
        ExtractedField(
            field_name="email",
            value="girisha@example.com",
            source="local_mock",
            confidence=0.90,
        ),
        ExtractedField(
            field_name="phone",
            value="+1234567890",
            source="local_mock",
            confidence=0.88,
        ),
    ]

    return ExtractedDocument(document_id=document_id, fields=fields)
