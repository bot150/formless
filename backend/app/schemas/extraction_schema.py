from pydantic import BaseModel


class ExtractedField(BaseModel):
    field_name: str
    value: str
    source: str = "local_mock"
    confidence: float


class ExtractedDocument(BaseModel):
    document_id: str
    fields: list[ExtractedField]


class DetectedFormField(BaseModel):
    field_name: str
    label: str
    field_type: str
    required: bool = True


class DetectedForm(BaseModel):
    form_id: str
    fields: list[DetectedFormField]
