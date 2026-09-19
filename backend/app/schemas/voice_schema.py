from pydantic import BaseModel


class VoiceTranscription(BaseModel):
    text: str
    confidence: float = 0.95
    source: str = "local_mock"
