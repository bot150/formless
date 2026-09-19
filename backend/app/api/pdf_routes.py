from fastapi import APIRouter

router = APIRouter(tags=["pdf"])


@router.post("/applications/{application_id}/pdf")
def generate_pdf(application_id: str) -> dict[str, str]:
    return {"application_id": application_id, "status": "queued"}
