"""
Local Mock Form Field Detection Service
NOTE: This is a MOCK/LOCAL implementation for empty form field detection.
No real OCR, Textract, or AI is performed yet.
"""

from app.schemas.extraction_schema import DetectedForm, DetectedFormField
from app.utils.file_utils import FORMS_DIR


def detect_form_fields(form_id: str) -> DetectedForm | None:
    """
    Detects mock form fields from an uploaded empty form.
    [MOCK/LOCAL DETECTION: Deterministic test data with clear mock schema]
    """
    # Verify the form was uploaded and exists in local temp storage
    form_exists = False
    if FORMS_DIR.exists():
        for file_path in FORMS_DIR.iterdir():
            if file_path.name.startswith(f"{form_id}_"):
                form_exists = True
                break

    if not form_exists:
        return None

    # Deterministic mock detected fields for an empty form to be filled
    fields = [
        DetectedFormField(
            field_name="full_name",
            label="Full Name",
            field_type="text",
            required=True,
        ),
        DetectedFormField(
            field_name="date_of_birth",
            label="Date of Birth",
            field_type="date",
            required=True,
        ),
        DetectedFormField(
            field_name="email",
            label="Email Address",
            field_type="email",
            required=True,
        ),
        DetectedFormField(
            field_name="phone",
            label="Phone Number",
            field_type="phone",
            required=True,
        ),
        DetectedFormField(
            field_name="address",
            label="Residential Address",
            field_type="text",
            required=True,
        ),
        DetectedFormField(
            field_name="student_id",
            label="Student ID",
            field_type="text",
            required=True,
        ),
    ]

    return DetectedForm(form_id=form_id, fields=fields)
