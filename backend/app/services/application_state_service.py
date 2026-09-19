"""
Application State Service (Local In-Memory)
Maintains temporary application state for generated question sets and submitted answers
keyed by (document_id, form_id).
NOTE: In-memory placeholder until AWS DynamoDB is integrated.
"""

from app.schemas.answer_schema import AnswerResponse
from app.schemas.question_schema import QuestionSet

# In-memory store: (document_id, form_id) -> QuestionSet
_QUESTION_SETS: dict[tuple[str, str], QuestionSet] = {}

# In-memory store: (document_id, form_id) -> dict[question_id, AnswerResponse]
_ANSWERS: dict[tuple[str, str], dict[str, AnswerResponse]] = {}


def _normalize_key(document_id: str, form_id: str) -> tuple[str, str]:
    return (str(document_id).strip(), str(form_id).strip())


def get_question_set(document_id: str, form_id: str) -> QuestionSet | None:
    """
    Retrieve stored QuestionSet for a given (document_id, form_id) application.
    """
    return _QUESTION_SETS.get(_normalize_key(document_id, form_id))


def save_question_set(
    document_id: str,
    form_id: str,
    question_set: QuestionSet,
) -> QuestionSet:
    """
    Store the generated QuestionSet in state for a (document_id, form_id) application.
    """
    _QUESTION_SETS[_normalize_key(document_id, form_id)] = question_set
    return question_set


def save_answer_state(
    document_id: str,
    form_id: str,
    answer: AnswerResponse,
) -> AnswerResponse:
    """
    Save an accepted answer in state for future retrieval or form filling.
    """
    key = _normalize_key(document_id, form_id)
    if key not in _ANSWERS:
        _ANSWERS[key] = {}
    _ANSWERS[key][answer.question_id] = answer
    return answer


def get_answers_state(
    document_id: str,
    form_id: str,
) -> list[AnswerResponse]:
    """
    Retrieve all submitted answers for a (document_id, form_id) application.
    """
    return list(_ANSWERS.get(_normalize_key(document_id, form_id), {}).values())


def clear_application_state() -> None:
    """
    Resets the in-memory state (used for testing isolation).
    """
    _QUESTION_SETS.clear()
    _ANSWERS.clear()
