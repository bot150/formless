from dataclasses import dataclass


@dataclass
class AnswerModel:
    field_name: str
    value: object
    confidence: float
    source: str | None = None
