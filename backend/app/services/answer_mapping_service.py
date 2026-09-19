from app.schemas.answer_schema import Answer


def map_answer(field_name: str, value: object, confidence: float = 1.0, source: str | None = None) -> Answer:
    return Answer(field_name=field_name, value=str(value), confidence=confidence, source=source)
