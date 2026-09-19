from fastapi import APIRouter, HTTPException, status

from app.schemas.matching_schema import MatchingResult
from app.services.document_extraction_service import extract_document_data
from app.services.form_extraction_service import detect_form_fields
from app.services.matching_service import match_fields

router = APIRouter(tags=["matching"])


@router.get(
    "/api/applications/{document_id}/{form_id}/matching",
    response_model=MatchingResult,
    summary="Match extracted document data against detected form fields",
)
def get_application_matching(document_id: str, form_id: str) -> MatchingResult:
    """
    Compares extracted data from an uploaded information document with detected fields
    from an uploaded empty form. Returns matched and missing fields.
    """
    extracted_doc = extract_document_data(document_id)
    if not extracted_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found. Please upload the document first.",
        )

    detected_form = detect_form_fields(form_id)
    if not detected_form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Form '{form_id}' not found. Please upload the form first.",
        )

    return match_fields(extracted_doc, detected_form)
