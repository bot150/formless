from fastapi import APIRouter, File, UploadFile

from app.utils.file_utils import DOCUMENTS_DIR, save_upload_file, validate_file_type

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    content_type = validate_file_type(file)
    document_id, _, _ = await save_upload_file(file, DOCUMENTS_DIR)

    return {
        "document_id": document_id,
        "filename": file.filename,
        "content_type": content_type,
    }
