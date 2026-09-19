"""
Answer Processing Service
NOTE: This service handles answer cleaning and deterministic validation for both
typed text and future voice transcription inputs without using AI models.
"""

import re
from datetime import datetime
from typing import Literal

from app.schemas.answer_schema import AnswerResponse

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_REGEX = re.compile(r"^\+?[0-9]{7,15}$")
BOOLEAN_TRUE_VALUES = {"true", "yes", "y", "1"}
BOOLEAN_FALSE_VALUES = {"false", "no", "n", "0"}

DATE_FORMATS = [
    "%d/%m/%Y",
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%m/%d/%Y",
]


def validate_field_value(
    value: str,
    field_type: str = "text",
    options: list[str] | None = None,
) -> str:
    """
    Validates the field value against the expected field type.
    Strips leading/trailing whitespace and raises ValueError on invalid inputs.
    """
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Answer cannot be empty.")

    f_type = field_type.strip().lower()

    if f_type == "text":
        return cleaned

    elif f_type == "number":
        try:
            float(cleaned)
            return cleaned
        except ValueError:
            raise ValueError(f"'{cleaned}' is not a valid number.")

    elif f_type == "date":
        is_valid = False
        for fmt in DATE_FORMATS:
            try:
                datetime.strptime(cleaned, fmt)
                is_valid = True
                break
            except ValueError:
                pass
        if not is_valid:
            raise ValueError(
                f"'{cleaned}' is not a valid date. Expected formats: DD/MM/YYYY or YYYY-MM-DD."
            )
        return cleaned

    elif f_type == "email":
        if not EMAIL_REGEX.match(cleaned):
            raise ValueError(f"'{cleaned}' is not a valid email address.")
        return cleaned

    elif f_type == "phone":
        digits_only = re.sub(r"[\s\-\(\)]", "", cleaned)
        if not PHONE_REGEX.match(digits_only):
            raise ValueError(f"'{cleaned}' is not a valid phone number.")
        return cleaned

    elif f_type == "boolean":
        lower = cleaned.lower()
        if lower not in BOOLEAN_TRUE_VALUES and lower not in BOOLEAN_FALSE_VALUES:
            raise ValueError(
                f"'{cleaned}' is not a valid boolean. Expected yes/no or true/false."
            )
        return cleaned

    elif f_type == "select":
        if options:
            normalized_options = [opt.lower() for opt in options]
            if cleaned.lower() not in normalized_options:
                raise ValueError(
                    f"'{cleaned}' is not a valid selection. Allowed options: {options}"
                )
        return cleaned

    return cleaned


def process_answer(
    question_id: str,
    field_name: str,
    answer: str,
    source: Literal["text", "voice"],
    field_type: str = "text",
    options: list[str] | None = None,
) -> AnswerResponse:
    """
    Cleans, validates, and processes an answer submitted via text or voice.
    """
    cleaned_answer = validate_field_value(answer, field_type, options)

    return AnswerResponse(
        question_id=question_id,
        field_name=field_name,
        answer=cleaned_answer,
        source=source,
        status="accepted",
    )
