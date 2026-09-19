import pytest
from fastapi import UploadFile

from app.services.transcribe_service import transcribe_audio


@pytest.mark.asyncio
async def test_voice_transcription_returns_text() -> None:
    transcription = await transcribe_audio(UploadFile(filename="answer.wav"))
    assert "answer.wav" in transcription.text
