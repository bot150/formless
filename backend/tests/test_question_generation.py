import io
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.matching_schema import MissingField
from app.schemas.question_schema import QuestionSet
from app.services.question_service import (
    generate_question_text,
    generate_questions_for_missing_fields,
)

client = TestClient(app)

DUMMY_PDF = b"%PDF-1.4 sample pdf for question generation"


def test_unit_generate_questions_for_missing_fields():
    missing = [
        MissingField(
            field_name="address",
            form_label="Address",
            field_type="text",
            required=True,
        ),
        MissingField(
            field_name="student_id",
            form_label="Student ID",
            field_type="text",
            required=False,
        ),
    ]

    q_set = generate_questions_for_missing_fields("doc-123", "form-456", missing)
    assert q_set.document_id == "doc-123"
    assert q_set.form_id == "form-456"
    assert len(q_set.questions) == 2

    q1 = q_set.questions[0]
    assert q1.field_name == "address"
    assert q1.form_label == "Address"
    assert q1.field_type == "text"
    assert q1.required is True
    assert q1.question_text == "What is your address?"

    q2 = q_set.questions[1]
    assert q2.field_name == "student_id"
    assert q2.form_label == "Student ID"
    assert q2.field_type == "text"
    assert q2.required is False
    assert q2.question_text == "What is your student ID?"

    # Ensure question IDs are non-empty and unique
    assert q1.question_id != q2.question_id
    assert len(q1.question_id) > 10


def test_unit_question_text_templates():
    assert generate_question_text("date_of_birth", "Date of Birth") == "What is your date of birth?"
    assert generate_question_text("phone", "Phone") == "What is your phone number?"
    assert generate_question_text("email", "Email") == "What is your email address?"
    assert generate_question_text("unknown_field", "Guardian Name") == "What is your Guardian Name?"


def test_api_questions_generated_only_for_missing_fields():
    # 1. Upload document (mock data contains: full_name, date_of_birth, email, phone)
    doc_res = client.post(
        "/api/documents/upload",
        files={"file": ("passport.pdf", io.BytesIO(DUMMY_PDF), "application/pdf")},
    )
    assert doc_res.status_code == 200
    doc_id = doc_res.json()["document_id"]

    # 2. Upload form (mock data contains: full_name, date_of_birth, email, phone, address, student_id)
    form_res = client.post(
        "/api/forms/upload",
        files={"file": ("admission.pdf", io.BytesIO(DUMMY_PDF), "application/pdf")},
    )
    assert form_res.status_code == 200
    form_id = form_res.json()["form_id"]

    # 3. Call questions generation API
    res = client.get(f"/api/applications/{doc_id}/{form_id}/questions")
    assert res.status_code == 200

    data = res.json()
    validated = QuestionSet.model_validate(data)

    assert validated.document_id == doc_id
    assert validated.form_id == form_id

    # Matched fields: full_name, date_of_birth, email, phone
    # Missing fields: address, student_id
    # Questions MUST ONLY be generated for missing fields
    question_fields = [q.field_name for q in validated.questions]
    assert question_fields == ["address", "student_id"]

    # Verify matched fields do NOT produce questions
    assert "full_name" not in question_fields
    assert "date_of_birth" not in question_fields
    assert "email" not in question_fields
    assert "phone" not in question_fields

    # Verify question content and preserved order
    assert validated.questions[0].question_text == "What is your address?"
    assert validated.questions[0].field_type == "text"
    assert validated.questions[0].required is True

    assert validated.questions[1].question_text == "What is your student ID?"
    assert validated.questions[1].field_type == "text"
    assert validated.questions[1].required is True

    # Verify unique IDs
    ids = [q.question_id for q in validated.questions]
    assert len(ids) == len(set(ids))


def test_api_questions_nonexistent_document_returns_404():
    form_res = client.post(
        "/api/forms/upload",
        files={"file": ("valid_form.pdf", io.BytesIO(DUMMY_PDF), "application/pdf")},
    )
    form_id = form_res.json()["form_id"]

    res = client.get(f"/api/applications/nonexistent-doc-uuid/{form_id}/questions")
    assert res.status_code == 404
    assert "document" in res.json()["detail"].lower()


def test_api_questions_nonexistent_form_returns_404():
    doc_res = client.post(
        "/api/documents/upload",
        files={"file": ("valid_doc.pdf", io.BytesIO(DUMMY_PDF), "application/pdf")},
    )
    doc_id = doc_res.json()["document_id"]

    res = client.get(f"/api/applications/{doc_id}/nonexistent-form-uuid/questions")
    assert res.status_code == 404
    assert "form" in res.json()["detail"].lower()
