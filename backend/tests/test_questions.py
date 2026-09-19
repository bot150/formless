from app.services.question_service import list_questions


def test_questions_are_scoped_to_application() -> None:
    questions = list_questions("demo-001")
    assert questions[0].question_id == "demo-001-occupation"
