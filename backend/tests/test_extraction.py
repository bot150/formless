import io
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.extraction_schema import DetectedForm, ExtractedDocument

client = TestClient(app)

DUMMY_PDF = b"%PDF-1.4 mock pdf data"


def test_valid_document_extraction():
    # 1. Upload a document first
    upload_res = client.post(
        "/api/documents/upload",
        files={"file": ("id_proof.pdf", io.BytesIO(DUMMY_PDF), "application/pdf")},
    )
    assert upload_res.status_code == 200
    document_id = upload_res.json()["document_id"]

    # 2. Query extracted data
    res = client.get(f"/api/documents/{document_id}/extracted-data")
    assert res.status_code == 200

    data = res.json()
    assert data["document_id"] == document_id
    assert isinstance(data["fields"], list)
    assert len(data["fields"]) >= 4

    # Verify field contents
    field_names = [f["field_name"] for f in data["fields"]]
    assert "full_name" in field_names
    assert "date_of_birth" in field_names
    assert "email" in field_names
    assert "phone" in field_names

    # Check field attributes
    for field in data["fields"]:
        assert "field_name" in field
        assert "value" in field
        assert field["source"] == "local_mock"
        assert isinstance(field["confidence"], (int, float))
        assert 0.0 <= field["confidence"] <= 1.0

    # Verify schema with Pydantic model
    validated = ExtractedDocument(**data)
    assert validated.document_id == document_id


def test_valid_form_field_detection():
    # 1. Upload a form first
    upload_res = client.post(
        "/api/forms/upload",
        files={"file": ("admission_form.pdf", io.BytesIO(DUMMY_PDF), "application/pdf")},
    )
    assert upload_res.status_code == 200
    form_id = upload_res.json()["form_id"]

    # 2. Query detected fields
    res = client.get(f"/api/forms/{form_id}/detected-fields")
    assert res.status_code == 200

    data = res.json()
    assert data["form_id"] == form_id
    assert isinstance(data["fields"], list)
    assert len(data["fields"]) >= 6

    # Verify detected field names
    field_names = [f["field_name"] for f in data["fields"]]
    assert "full_name" in field_names
    assert "date_of_birth" in field_names
    assert "email" in field_names
    assert "phone" in field_names
    assert "address" in field_names
    assert "student_id" in field_names

    # Check detected field structure
    for field in data["fields"]:
        assert "field_name" in field
        assert "label" in field
        assert "field_type" in field
        assert "required" in field
        assert isinstance(field["required"], bool)

    # Verify schema with Pydantic model
    validated = DetectedForm(**data)
    assert validated.form_id == form_id


def test_nonexistent_document_returns_404():
    res = client.get("/api/documents/nonexistent-doc-uuid-9999/extracted-data")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_nonexistent_form_returns_404():
    res = client.get("/api/forms/nonexistent-form-uuid-9999/detected-fields")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_response_schema_structure():
    # Upload and verify both schemas validate against Pydantic models
    doc_upload = client.post(
        "/api/documents/upload",
        files={"file": ("doc.pdf", io.BytesIO(DUMMY_PDF), "application/pdf")},
    )
    doc_id = doc_upload.json()["document_id"]
    doc_data = client.get(f"/api/documents/{doc_id}/extracted-data").json()
    doc_model = ExtractedDocument.model_validate(doc_data)
    assert doc_model.document_id == doc_id

    form_upload = client.post(
        "/api/forms/upload",
        files={"file": ("form.pdf", io.BytesIO(DUMMY_PDF), "application/pdf")},
    )
    form_id = form_upload.json()["form_id"]
    form_data = client.get(f"/api/forms/{form_id}/detected-fields").json()
    form_model = DetectedForm.model_validate(form_data)
    assert form_model.form_id == form_id
