from fastapi import APIRouter

router = APIRouter(tags=["applications"])


@router.get("/applications/{application_id}")
def get_application(application_id: str) -> dict[str, str]:
    return {"application_id": application_id, "status": "pending"}
