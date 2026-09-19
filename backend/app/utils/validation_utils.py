def validate_required(value: object, field_name: str) -> object:
    if value is None or value == "":
        raise ValueError(f"{field_name} is required")
    return value
