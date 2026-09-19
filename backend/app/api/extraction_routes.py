from fastapi import APIRouter, HTTPException, status

from app.schemas.extraction_schema import DetectedForm, ExtractedDocument
from app.services.document_extraction_service import extract_document_data
from app.services.form_extraction_service import detect_form_fields

router = APIRouter(tags=["extraction"])


@router.get(
    "/api/documents/{document_id}/extracted-data",
    response_model=ExtractedDocument,
    summary="Get extracted data from an information document (Mock/Local)",
)
def get_extracted_document_data(document_id: str) -> ExtractedDocument:
    """
    Returns extracted fields from an uploaded information document.
    [MOCK/LOCAL EXTRACTION: Placeholder until OCR/AWS services are integrated]
    """
    extracted = extract_document_data(document_id)
    if not extracted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found. Please upload the document first.",
        )
    return extracted


@router.get(
    "/api/forms/{form_id}/detected-fields",
    response_model=DetectedForm,
    summary="Get detected fields from an empty form (Mock/Local)",
)
def get_detected_form_fields(form_id: str) -> DetectedForm:
    """
    Returns detected fields from an uploaded empty form.
    [MOCK/LOCAL DETECTION: Placeholder until OCR/AWS services are integrated]
    """
    detected = detect_form_fields(form_id)
    if not detected:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Form '{form_id}' not found. Please upload the form first.",
        )
    return detected
