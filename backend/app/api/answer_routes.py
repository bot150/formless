from fastapi import APIRouter, HTTPException, status

from app.schemas.answer_schema import Answer, AnswerRequest, AnswerResponse
from app.services.answer_service import process_answer
from app.services.application_state_service import (
    get_question_set,
    save_answer_state,
)
from app.services.document_extraction_service import extract_document_data
from app.services.form_extraction_service import detect_form_fields

router = APIRouter(tags=["answers"])


@router.post(
    "/api/applications/{document_id}/{form_id}/answers",
    response_model=AnswerResponse,
    summary="Submit and validate an answer to a generated question",
)
def submit_answer(
    document_id: str,
    form_id: str,
    request: AnswerRequest,
) -> AnswerResponse:
    """
    Submits an answer for a specific generated question.
    Retrieves the previously stored question set (without regenerating).
    Validates question_id, field_name, and field_type value.
    """
    # 1. Verify document exists
    extracted_doc = extract_document_data(document_id)
    if not extracted_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found. Please upload the document first.",
        )

    # 2. Verify form exists
    detected_form = detect_form_fields(form_id)
    if not detected_form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Form '{form_id}' not found. Please upload the form first.",
        )

    # 3. Retrieve previously stored question set (DO NOT regenerate)
    question_set = get_question_set(document_id, form_id)
    if not question_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question '{request.question_id}' not found for this application.",
        )

    # 4. Verify question_id belongs to the stored question set
    target_qid = request.question_id.strip()
    question = next(
        (q for q in question_set.questions if q.question_id.strip() == target_qid),
        None,
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question '{request.question_id}' not found for this application.",
        )

    # 5. Verify field_name matches the question
    if request.field_name != question.field_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Field name '{request.field_name}' does not match question field '{question.field_name}'.",
        )

    # 6. Validate answer according to field type
    try:
        response = process_answer(
            question_id=request.question_id,
            field_name=request.field_name,
            answer=request.answer,
            source=request.source,
            field_type=question.field_type,
        )
        # Store accepted answer in application state
        save_answer_state(document_id, form_id, response)
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# Retained for legacy backward compatibility
@router.post("/applications/{application_id}/answers", response_model=Answer)
def save_legacy_answer(application_id: str, answer: Answer) -> Answer:
    return answer
