import io
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.extraction_schema import (
    DetectedForm,
    DetectedFormField,
    ExtractedDocument,
    ExtractedField,
)
from app.schemas.matching_schema import MatchingResult
from app.services.matching_service import match_fields

client = TestClient(app)

DUMMY_PDF = b"%PDF-1.4 sample pdf for matching"


def test_unit_exact_field_matching():
    extracted = ExtractedDocument(
        document_id="doc-1",
        fields=[
            ExtractedField(
                field_name="full_name",
                value="Alice Smith",
                source="local_mock",
                confidence=0.95,
            ),
        ],
    )
    form = DetectedForm(
        form_id="form-1",
        fields=[
            DetectedFormField(
                field_name="full_name",
                label="Full Name",
                field_type="text",
                required=True,
            ),
        ],
    )
    result = match_fields(extracted, form)
    assert len(result.matched_fields) == 1
    assert result.matched_fields[0].field_name == "full_name"
    assert result.matched_fields[0].value == "Alice Smith"
    assert result.matched_fields[0].confidence == 1.0  # Exact match score
    assert result.matched_fields[0].status == "matched"
    assert len(result.missing_fields) == 0


def test_unit_alias_field_matching():
    # Alias pairs: "name" <-> "full_name", "dob" <-> "date_of_birth", "mobile" <-> "phone"
    extracted = ExtractedDocument(
        document_id="doc-2",
        fields=[
            ExtractedField(
                field_name="name",
                value="Bob Jones",
                source="local_mock",
                confidence=0.9,
            ),
            ExtractedField(
                field_name="dob",
                value="1999-05-20",
                source="local_mock",
                confidence=0.9,
            ),
            ExtractedField(
                field_name="mobile",
                value="+1987654321",
                source="local_mock",
                confidence=0.9,
            ),
        ],
    )
    form = DetectedForm(
        form_id="form-2",
        fields=[
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
                field_name="phone",
                label="Phone Number",
                field_type="phone",
                required=True,
            ),
        ],
    )
    result = match_fields(extracted, form)
    assert len(result.matched_fields) == 3
    for mf in result.matched_fields:
        assert mf.confidence == 0.9  # Alias match score
        assert mf.status == "matched"
    assert len(result.missing_fields) == 0


def test_unit_missing_field_detection():
    extracted = ExtractedDocument(
        document_id="doc-3",
        fields=[
            ExtractedField(
                field_name="full_name",
                value="Charlie",
                source="local_mock",
                confidence=0.95,
            ),
        ],
    )
    form = DetectedForm(
        form_id="form-3",
        fields=[
            DetectedFormField(
                field_name="full_name",
                label="Full Name",
                field_type="text",
                required=True,
            ),
            DetectedFormField(
                field_name="address",
                label="Address",
                field_type="text",
                required=True,
            ),
            DetectedFormField(
                field_name="student_id",
                label="Student ID",
                field_type="text",
                required=False,
            ),
        ],
    )
    result = match_fields(extracted, form)
    assert len(result.matched_fields) == 1
    assert result.matched_fields[0].field_name == "full_name"

    assert len(result.missing_fields) == 2
    missing_names = [f.field_name for f in result.missing_fields]
    assert "address" in missing_names
    assert "student_id" in missing_names


def test_api_matching_complete_response():
    # 1. Upload document
    doc_res = client.post(
        "/api/documents/upload",
        files={"file": ("passport.pdf", io.BytesIO(DUMMY_PDF), "application/pdf")},
    )
    assert doc_res.status_code == 200
    doc_id = doc_res.json()["document_id"]

    # 2. Upload form
    form_res = client.post(
        "/api/forms/upload",
        files={"file": ("admission.pdf", io.BytesIO(DUMMY_PDF), "application/pdf")},
    )
    assert form_res.status_code == 200
    form_id = form_res.json()["form_id"]

    # 3. Call matching API
    res = client.get(f"/api/applications/{doc_id}/{form_id}/matching")
    assert res.status_code == 200

    data = res.json()
    assert data["document_id"] == doc_id
    assert data["form_id"] == form_id

    # Validate against MatchingResult Pydantic model
    validated = MatchingResult.model_validate(data)
    assert validated.document_id == doc_id

    # Mock doc has: full_name, date_of_birth, email, phone
    # Mock form has: full_name, date_of_birth, email, phone, address, student_id
    matched_names = [f.field_name for f in validated.matched_fields]
    assert matched_names == ["full_name", "date_of_birth", "email", "phone"]
    for f in validated.matched_fields:
        assert f.confidence == 1.0
        assert f.status == "matched"

    missing_names = [f.field_name for f in validated.missing_fields]
    assert missing_names == ["address", "student_id"]


def test_api_nonexistent_document_returns_404():
    form_res = client.post(
        "/api/forms/upload",
        files={"file": ("valid_form.pdf", io.BytesIO(DUMMY_PDF), "application/pdf")},
    )
    form_id = form_res.json()["form_id"]

    res = client.get(f"/api/applications/nonexistent-doc-uuid/{form_id}/matching")
    assert res.status_code == 404
    assert "document" in res.json()["detail"].lower()


def test_api_nonexistent_form_returns_404():
    doc_res = client.post(
        "/api/documents/upload",
        files={"file": ("valid_doc.pdf", io.BytesIO(DUMMY_PDF), "application/pdf")},
    )
    doc_id = doc_res.json()["document_id"]

    res = client.get(f"/api/applications/{doc_id}/nonexistent-form-uuid/matching")
    assert res.status_code == 404
    assert "form" in res.json()["detail"].lower()
