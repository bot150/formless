def save_application(application_id: str, data: dict[str, object]) -> dict[str, object]:
    return {"application_id": application_id, **data}
