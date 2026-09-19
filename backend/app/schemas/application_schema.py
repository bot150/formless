from pydantic import BaseModel


class DocumentProcessingRequest(BaseModel):
    application_id: str
    form_id: str
    document_ids: list[str]


class ApplicationResponse(BaseModel):
    application_id: str
    status: str
    total_fields: int
    filled_fields: int
    missing_fields: list[str]
    fields: dict[str, dict[str, object]]
