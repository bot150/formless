"""
Local Mock Voice Transcription Service
NOTE: This is a local mock speech-to-text layer for local development and testing.
AWS Transcribe integration is postponed until later.
No external speech API is called.
"""

import os
from fastapi import HTTPException, UploadFile, status

from app.schemas.voice_schema import VoiceTranscription

ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".webm"}
ALLOWED_AUDIO_CONTENT_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/webm",
}


def validate_audio_file(file: UploadFile) -> str:
    """
    Validates that the uploaded audio file has an allowed extension and content type.
    Allowed formats: wav, mp3, m4a, webm.
    Raises HTTP 400 on unsupported formats.
    """
    filename = file.filename or ""
    extension = os.path.splitext(filename)[1].lower() if filename else ""

    if not extension or extension not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format '{extension}'. Allowed formats: wav, mp3, m4a, webm.",
        )

    content_type = file.content_type
    if (
        content_type
        and content_type != "application/octet-stream"
        and content_type not in ALLOWED_AUDIO_CONTENT_TYPES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio content type '{content_type}'. Allowed: wav, mp3, m4a, webm.",
        )

    return extension


async def transcribe_audio(
    audio: UploadFile,
    test_transcript: str | None = None,
) -> VoiceTranscription:
    """
    Local mock speech-to-text service.
    Accepts an audio file and an optional simulated test transcript for local development/testing.
    Clearly marked with source='local_mock'. No external speech API is called.
    """
    # If a test transcript is supplied (explicitly testing), use it
    if test_transcript is not None:
        return VoiceTranscription(
            text=test_transcript.strip(),
            confidence=0.95,
            source="local_mock",
        )

    # Deterministic local mock transcription for development
    filename = (audio.filename or "").lower()
    if "address" in filename:
        mock_text = "Vijayawada, Andhra Pradesh"
    elif "student" in filename or "id" in filename:
        mock_text = "STU-98765"
    else:
        mock_text = "Vijayawada, Andhra Pradesh"

    return VoiceTranscription(
        text=mock_text,
        confidence=0.95,
        source="local_mock",
    )
