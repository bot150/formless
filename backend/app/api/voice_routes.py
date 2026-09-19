from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.schemas.answer_schema import AnswerResponse
from app.schemas.voice_schema import VoiceTranscription
from app.services.answer_service import process_answer
from app.services.application_state_service import (
    get_question_set,
    save_answer_state,
)
from app.services.document_extraction_service import extract_document_data
from app.services.form_extraction_service import detect_form_fields
from app.services.transcribe_service import transcribe_audio as legacy_transcribe_audio
from app.services.voice_service import transcribe_audio, validate_audio_file

router = APIRouter(tags=["voice"])


@router.post(
    "/api/applications/{document_id}/{form_id}/voice-answer",
    response_model=AnswerResponse,
    summary="Submit a voice audio answer for a generated question",
)
async def submit_voice_answer(
    document_id: str,
    form_id: str,
    question_id: str = Form(...),
    field_name: str = Form(...),
    audio: UploadFile = File(...),
    test_transcript: str | None = Form(None),
) -> AnswerResponse:
    """
    Submits a voice audio answer for a generated question.
    Transcribes audio via the speech-to-text layer (local/mock) and passes the resulting
    transcript into the existing answer_service for validation and processing.
    """
    # 1. Validate audio file format
    validate_audio_file(audio)

    # 2. Verify document exists
    extracted_doc = extract_document_data(document_id)
    if not extracted_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found. Please upload the document first.",
        )

    # 3. Verify form exists
    detected_form = detect_form_fields(form_id)
    if not detected_form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Form '{form_id}' not found. Please upload the form first.",
        )

    # 4. Retrieve stored question set
    question_set = get_question_set(document_id, form_id)
    if not question_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question '{question_id}' not found for this application.",
        )

    # 5. Verify question_id belongs to the stored question set
    target_qid = question_id.strip()
    question = next(
        (q for q in question_set.questions if q.question_id.strip() == target_qid),
        None,
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question '{question_id}' not found for this application.",
        )

    # 6. Verify field_name matches the question
    if field_name != question.field_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Field name '{field_name}' does not match question field '{question.field_name}'.",
        )

    # 7. Speech-to-text transcription (local mock)
    transcription = await transcribe_audio(audio, test_transcript=test_transcript)

    # 8. Check for empty transcript
    if not transcription.text or not transcription.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Speech-to-text produced an empty transcript. Please speak clearly and try again.",
        )

    # 9. Reuse existing answer_service for validation and processing
    try:
        response = process_answer(
            question_id=question_id,
            field_name=field_name,
            answer=transcription.text,
            source="voice",
            field_type=question.field_type,
        )
        save_answer_state(document_id, form_id, response)
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# Retained for legacy backward compatibility
@router.post("/voice/transcribe", response_model=VoiceTranscription)
async def transcribe_voice(audio: UploadFile) -> VoiceTranscription:
    return await legacy_transcribe_audio(audio)
