import uuid

from app.schemas.matching_schema import MissingField
from app.schemas.question_schema import Question, QuestionSet

KNOWN_QUESTION_TEMPLATES: dict[str, str] = {
    "address": "What is your address?",
    "residential_address": "What is your address?",
    "student_id": "What is your student ID?",
    "registration_number": "What is your registration number?",
    "date_of_birth": "What is your date of birth?",
    "dob": "What is your date of birth?",
    "phone": "What is your phone number?",
    "phone_number": "What is your phone number?",
    "mobile": "What is your mobile number?",
    "email": "What is your email address?",
    "email_address": "What is your email address?",
    "full_name": "What is your full name?",
    "name": "What is your full name?",
    "occupation": "What is your occupation?",
}


def generate_question_text(field_name: str, form_label: str) -> str:
    """
    Generates a natural question prompt for a missing form field.
    Uses known conversational templates for standard fields, or falls back to
    'What is your {form_label}?' for unknown fields.
    """
    norm = field_name.strip().lower().replace("-", "_").replace(" ", "_")
    if norm in KNOWN_QUESTION_TEMPLATES:
        return KNOWN_QUESTION_TEMPLATES[norm]
    label = form_label.strip() if form_label else field_name.replace("_", " ").title()
    return f"What is your {label}?"


def generate_questions_for_missing_fields(
    document_id: str,
    form_id: str,
    missing_fields: list[MissingField],
) -> QuestionSet:
    """
    Generates Question models only for missing form fields, preserving their original form order.
    Each generated question receives a unique UUID.
    """
    questions: list[Question] = []
    for field in missing_fields:
        q_id = str(uuid.uuid4())
        q_text = generate_question_text(field.field_name, field.form_label)
        questions.append(
            Question(
                question_id=q_id,
                field_name=field.field_name,
                form_label=field.form_label,
                field_type=field.field_type,
                required=field.required,
                question_text=q_text,
                label=q_text,
            )
        )

    return QuestionSet(
        document_id=document_id,
        form_id=form_id,
        questions=questions,
    )


# Retained for legacy test backward compatibility
def list_questions(application_id: str) -> list[Question]:
    return [
        Question(
            question_id=f"{application_id}-occupation",
            field_name="occupation",
            form_label="Occupation",
            field_type="text",
            required=True,
            question_text="What is your occupation?",
            label="What is your occupation?",
        )
    ]
