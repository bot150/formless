from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.schemas.form_schema import FormSchema
from app.services.form_service import get_form_schema, student_application
from app.utils.file_utils import FORMS_DIR, save_upload_file, validate_file_type

router = APIRouter(prefix="/api/forms", tags=["forms"])


@router.post("/upload")
async def upload_form(file: UploadFile = File(...)):
    content_type = validate_file_type(file)
    form_id, _, _ = await save_upload_file(file, FORMS_DIR)

    return {
        "form_id": form_id,
        "filename": file.filename,
        "content_type": content_type,
    }


@router.get("/student_application", response_model=FormSchema)
def get_student_application():
    return student_application


@router.get("/{form_id}", response_model=FormSchema)
def get_form(form_id: str):
    form = get_form_schema(form_id)
    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Form '{form_id}' not found",
        )
    return form
