import logging
from typing import Optional
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.user import Profile, User
from app.schemas.auth_schema import (
    ProfileConfirmRequest,
    ProfileResponse,
    UserProfileDetailsResponse,
)

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}


def extract_aadhaar_mock(
    file: UploadFile,
    file_bytes: bytes,
) -> ProfileResponse:
    """Mock/local Aadhaar extraction service.

    Processes an uploaded Aadhaar card image/PDF and extracts fields without
    retaining the image file or logging sensitive identity numbers.
    """
    filename = (file.filename or "").lower()
    if not any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Allowed formats: JPG, JPEG, PNG, PDF.",
        )

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # Check for test trigger for corrupt / unreadable document
    file_bytes_lower = file_bytes.lower()
    if b"corrupt" in file_bytes_lower or b"unreadable" in file_bytes_lower:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corrupt or unreadable document. Please upload a clear document.",
        )

    # Check for test trigger where OCR detects no fields or misses required fields (422)
    if b"no_fields" in file_bytes_lower or b"unrecognized" in file_bytes_lower:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "success": False,
                "message": "Unable to extract Aadhaar details. Please upload a clear document.",
                "extracted_fields": {},
                "missing_fields": ["name", "date_of_birth", "gender", "address"],
            },
        )

    if b"missing_name" in file_bytes_lower:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "success": False,
                "message": "Required fields could not be extracted from document.",
                "extracted_fields": {
                    "date_of_birth": "04/07/2007",
                    "gender": "Female",
                    "address": "Vijayawada, Andhra Pradesh",
                },
                "missing_fields": ["name"],
            },
        )

    # In local mock mode, simulate successful OCR output for verification
    logger.info("Local mock Aadhaar OCR completed successfully for processing.")

    from app.schemas.auth_schema import ExtractedFieldsData

    return ProfileResponse(
        success=True,
        message="Aadhaar details extracted successfully.",
        extracted_fields=ExtractedFieldsData(
            name="Example User",
            date_of_birth="04/07/2007",
            gender="Female",
            address="Vijayawada, Andhra Pradesh",
        ),
        missing_fields=[],
        source="local_mock",
    )


def save_or_update_profile(
    db: Session,
    user: User,
    profile_data: ProfileConfirmRequest,
) -> UserProfileDetailsResponse:
    """Save or update the authenticated user's confirmed profile details."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()

    if profile:
        profile.name = profile_data.name.strip()
        profile.date_of_birth = (
            profile_data.date_of_birth.strip() if profile_data.date_of_birth else None
        )
        profile.gender = (
            profile_data.gender.strip() if profile_data.gender else None
        )
        profile.address = (
            profile_data.address.strip() if profile_data.address else None
        )
    else:
        profile = Profile(
            user_id=user.id,
            name=profile_data.name.strip(),
            date_of_birth=profile_data.date_of_birth.strip()
            if profile_data.date_of_birth
            else None,
            gender=profile_data.gender.strip() if profile_data.gender else None,
            address=profile_data.address.strip() if profile_data.address else None,
        )
        db.add(profile)

    db.commit()
    db.refresh(profile)
    return UserProfileDetailsResponse.model_validate(profile)
