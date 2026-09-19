from fastapi import APIRouter, HTTPException, status

from app.schemas.question_schema import Question, QuestionSet
from app.services.application_state_service import (
    get_question_set,
    save_question_set,
)
from app.services.document_extraction_service import extract_document_data
from app.services.form_extraction_service import detect_form_fields
from app.services.matching_service import match_fields
from app.services.question_service import (
    generate_questions_for_missing_fields,
    list_questions,
)

router = APIRouter(tags=["questions"])


@router.get(
    "/api/applications/{document_id}/{form_id}/questions",
    response_model=QuestionSet,
    summary="Generate or retrieve questions for missing fields in a form",
)
def get_questions_for_missing_fields(document_id: str, form_id: str) -> QuestionSet:
    """
    Identifies missing fields between an uploaded document and empty form,
    generates conversational questions, stores them in application state,
    and returns the QuestionSet. Repeated calls return the same stored questions.
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

    # Return existing stored question set if already generated
    existing_qset = get_question_set(document_id, form_id)
    if existing_qset:
        return existing_qset

    matching_result = match_fields(extracted_doc, detected_form)
    question_set = generate_questions_for_missing_fields(
        document_id=document_id,
        form_id=form_id,
        missing_fields=matching_result.missing_fields,
    )

    # Persist in state service
    return save_question_set(document_id, form_id, question_set)


# Retained for legacy test backward compatibility
@router.get(
    "/api/applications/{application_id}/questions",
    response_model=list[Question],
)
def get_legacy_questions(application_id: str) -> list[Question]:
    return list_questions(application_id)
