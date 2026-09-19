from typing import Literal
from pydantic import BaseModel


class AnswerRequest(BaseModel):
    question_id: str
    field_name: str
    answer: str
    source: Literal["text", "voice"] = "text"


class AnswerResponse(BaseModel):
    question_id: str
    field_name: str
    answer: str
    source: Literal["text", "voice"]
    status: str = "accepted"


# Retained for legacy test backward compatibility
class Answer(BaseModel):
    field_name: str
    value: str | None = None
    confidence: float = 0.0
    source: str | None = None
