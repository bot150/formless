from fastapi import APIRouter

router = APIRouter(tags=["confirmation"])


@router.post("/applications/{application_id}/confirm")
def confirm_application(application_id: str) -> dict[str, str]:
    return {"application_id": application_id, "status": "confirmed"}
