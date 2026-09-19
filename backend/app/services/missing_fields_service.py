def find_missing_fields(required_fields: list[str], values: dict[str, object]) -> list[str]:
    return [field for field in required_fields if not values.get(field)]
