from app.services.answer_mapping_service import map_answer


def test_answer_mapping_preserves_metadata() -> None:
    answer = map_answer("name", "Rahul Kumar", 0.98, "aadhaar")
    assert answer.field_name == "name"
    assert answer.source == "aadhaar"
