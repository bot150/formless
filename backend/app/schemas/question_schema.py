from pydantic import BaseModel


class Question(BaseModel):
    question_id: str
    field_name: str
    form_label: str
    field_type: str
    required: bool
    question_text: str
    label: str | None = None  # retained for backward compatibility with legacy endpoints


class QuestionSet(BaseModel):
    document_id: str
    form_id: str
    questions: list[Question]
