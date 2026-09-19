from typing import Literal
from pydantic import BaseModel


class MatchedField(BaseModel):
    field_name: str
    form_label: str
    value: str
    source: str
    confidence: float
    status: Literal["matched", "missing"] = "matched"


class MissingField(BaseModel):
    field_name: str
    form_label: str
    field_type: str
    required: bool


class MatchingResult(BaseModel):
    document_id: str
    form_id: str
    matched_fields: list[MatchedField]
    missing_fields: list[MissingField]
