from fastapi import UploadFile

from app.schemas.voice_schema import VoiceTranscription


async def transcribe_audio(audio: UploadFile) -> VoiceTranscription:
    return VoiceTranscription(text=f"Transcription pending for {audio.filename or 'audio'}")
