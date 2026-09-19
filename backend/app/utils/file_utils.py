import os
import uuid
from pathlib import Path
from fastapi import HTTPException, UploadFile, status

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOCUMENTS_DIR = BASE_DIR / "temp" / "documents"
FORMS_DIR = BASE_DIR / "temp" / "forms"

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
}


def validate_file_type(file: UploadFile) -> str:
    filename = file.filename or ""
    extension = os.path.splitext(filename)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{extension}'. Allowed: PDF, PNG, JPG/JPEG.",
        )

    content_type = file.content_type
    if (
        content_type
        and content_type != "application/octet-stream"
        and content_type not in ALLOWED_CONTENT_TYPES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported content type '{content_type}'. Allowed: application/pdf, image/png, image/jpeg.",
        )

    if not content_type or content_type == "application/octet-stream":
        if extension == ".pdf":
            content_type = "application/pdf"
        elif extension == ".png":
            content_type = "image/png"
        elif extension in {".jpg", ".jpeg"}:
            content_type = "image/jpeg"

    return content_type


async def save_upload_file(file: UploadFile, target_dir: Path) -> tuple[str, str, Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid.uuid4())
    original_name = os.path.basename(file.filename or f"{file_id}.bin")
    saved_filename = f"{file_id}_{original_name}"
    saved_path = target_dir / saved_filename

    contents = await file.read()
    with open(saved_path, "wb") as f:
        f.write(contents)

    return file_id, saved_filename, saved_path
