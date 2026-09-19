import io
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.answer_schema import AnswerRequest, AnswerResponse
from app.services.answer_service import process_answer, validate_field_value
from app.services.application_state_service import clear_application_state

client = TestClient(app)

DUMMY_PDF = b"%PDF-1.4 sample pdf for answer submission"


@pytest.fixture(autouse=True)
def reset_state():
    clear_application_state()
    yield
    clear_application_state()


@pytest.fixture
def uploaded_setup():
    """Uploads sample document and form to set up valid test context."""
    doc_res = client.post(
        "/api/documents/upload",
        files={"file": ("passport.pdf", io.BytesIO(DUMMY_PDF), "application/pdf")},
    )
    assert doc_res.status_code == 200
    doc_id = doc_res.json()["document_id"]

    form_res = client.post(
        "/api/forms/upload",
        files={"file": ("admission.pdf", io.BytesIO(DUMMY_PDF), "application/pdf")},
    )
    assert form_res.status_code == 200
    form_id = form_res.json()["form_id"]

    q_res = client.get(f"/api/applications/{doc_id}/{form_id}/questions")
    assert q_res.status_code == 200
    questions = q_res.json()["questions"]

    return doc_id, form_id, questions


def test_question_id_stability_and_answer_submission():
    """
    Verifies that generated question IDs remain identical on subsequent retrievals,
    and submitting an answer with the returned question_id succeeds with HTTP 200.
    """
    doc_res = client.post(
        "/api/documents/upload",
        files={"file": ("passport.pdf", io.BytesIO(DUMMY_PDF), "application/pdf")},
    )
    doc_id = doc_res.json()["document_id"]

    form_res = client.post(
        "/api/forms/upload",
        files={"file": ("admission.pdf", io.BytesIO(DUMMY_PDF), "application/pdf")},
    )
    form_id = form_res.json()["form_id"]

    # Generate questions (first call)
    res1 = client.get(f"/api/applications/{doc_id}/{form_id}/questions")
    assert res1.status_code == 200
    q_set1 = res1.json()["questions"]

    # Retrieve questions again (second call)
    res2 = client.get(f"/api/applications/{doc_id}/{form_id}/questions")
    assert res2.status_code == 200
    q_set2 = res2.json()["questions"]

    # Verify identical question IDs
    assert len(q_set1) == len(q_set2)
    for q1, q2 in zip(q_set1, q_set2):
        assert q1["question_id"] == q2["question_id"]
        assert q1["field_name"] == q2["field_name"]

    # Submit an answer using the returned question_id
    address_q = next(q for q in q_set1 if q["field_name"] == "address")
    payload = {
        "question_id": address_q["question_id"],
        "field_name": "address",
        "answer": "Vijayawada, Andhra Pradesh",
        "source": "text",
    }
    ans_res = client.post(f"/api/applications/{doc_id}/{form_id}/answers", json=payload)
    assert ans_res.status_code == 200
    assert ans_res.json()["question_id"] == address_q["question_id"]
    assert ans_res.json()["status"] == "accepted"


def test_valid_text_answer_submission(uploaded_setup):
    doc_id, form_id, questions = uploaded_setup
    address_q = next(q for q in questions if q["field_name"] == "address")

    payload = {
        "question_id": address_q["question_id"],
        "field_name": "address",
        "answer": "  Vijayawada, Andhra Pradesh  ",
        "source": "text",
    }
    res = client.post(f"/api/applications/{doc_id}/{form_id}/answers", json=payload)
    assert res.status_code == 200

    data = res.json()
    assert data["question_id"] == address_q["question_id"]
    assert data["field_name"] == "address"
    assert data["answer"] == "Vijayawada, Andhra Pradesh"  # Whitespace stripped
    assert data["source"] == "text"
    assert data["status"] == "accepted"

    # Validate against Pydantic schema
    validated = AnswerResponse.model_validate(data)
    assert validated.status == "accepted"


def test_empty_answer_rejected(uploaded_setup):
    doc_id, form_id, questions = uploaded_setup
    address_q = next(q for q in questions if q["field_name"] == "address")

    # Empty string
    res = client.post(
        f"/api/applications/{doc_id}/{form_id}/answers",
        json={
            "question_id": address_q["question_id"],
            "field_name": "address",
            "answer": "   ",
            "source": "text",
        },
    )
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()


def test_invalid_question_id(uploaded_setup):
    doc_id, form_id, _ = uploaded_setup
    res = client.post(
        f"/api/applications/{doc_id}/{form_id}/answers",
        json={
            "question_id": "00000000-0000-0000-0000-000000000000",
            "field_name": "address",
            "answer": "Some Address",
            "source": "text",
        },
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_wrong_field_name(uploaded_setup):
    doc_id, form_id, questions = uploaded_setup
    address_q = next(q for q in questions if q["field_name"] == "address")

    res = client.post(
        f"/api/applications/{doc_id}/{form_id}/answers",
        json={
            "question_id": address_q["question_id"],
            "field_name": "wrong_field_name",
            "answer": "Some Value",
            "source": "text",
        },
    )
    assert res.status_code == 400
    assert "does not match" in res.json()["detail"].lower()


def test_document_not_found(uploaded_setup):
    _, form_id, questions = uploaded_setup
    address_q = next(q for q in questions if q["field_name"] == "address")

    res = client.post(
        f"/api/applications/nonexistent-doc/{form_id}/answers",
        json={
            "question_id": address_q["question_id"],
            "field_name": "address",
            "answer": "Some Value",
            "source": "text",
        },
    )
    assert res.status_code == 404
    assert "document" in res.json()["detail"].lower()


def test_form_not_found(uploaded_setup):
    doc_id, _, questions = uploaded_setup
    address_q = next(q for q in questions if q["field_name"] == "address")

    res = client.post(
        f"/api/applications/{doc_id}/nonexistent-form/answers",
        json={
            "question_id": address_q["question_id"],
            "field_name": "address",
            "answer": "Some Value",
            "source": "text",
        },
    )
    assert res.status_code == 404
    assert "form" in res.json()["detail"].lower()


def test_validation_email():
    assert validate_field_value("test@example.com", "email") == "test@example.com"
    with pytest.raises(ValueError):
        validate_field_value("invalid-email", "email")
    with pytest.raises(ValueError):
        validate_field_value("test@", "email")


def test_validation_phone():
    assert validate_field_value("+91 98765 43210", "phone") == "+91 98765 43210"
    assert validate_field_value("9876543210", "phone") == "9876543210"
    with pytest.raises(ValueError):
        validate_field_value("phone-number", "phone")
    with pytest.raises(ValueError):
        validate_field_value("123", "phone")


def test_validation_number():
    assert validate_field_value("42", "number") == "42"
    assert validate_field_value("3.1415", "number") == "3.1415"
    assert validate_field_value("-10", "number") == "-10"
    with pytest.raises(ValueError):
        validate_field_value("not-a-number", "number")


def test_validation_date():
    assert validate_field_value("15/01/2000", "date") == "15/01/2000"
    assert validate_field_value("2000-01-15", "date") == "2000-01-15"
    with pytest.raises(ValueError):
        validate_field_value("invalid-date", "date")
    with pytest.raises(ValueError):
        validate_field_value("32/01/2000", "date")


def test_validation_boolean():
    assert validate_field_value("yes", "boolean") == "yes"
    assert validate_field_value("no", "boolean") == "no"
    assert validate_field_value("true", "boolean") == "true"
    assert validate_field_value("false", "boolean") == "false"
    with pytest.raises(ValueError):
        validate_field_value("maybe", "boolean")


def test_source_voice_accepted_by_schema_and_service():
    resp = process_answer(
        question_id="voice-q-1",
        field_name="address",
        answer="New York, USA",
        source="voice",
        field_type="text",
    )
    assert resp.source == "voice"
    assert resp.status == "accepted"
    assert resp.answer == "New York, USA"

    # Verify Pydantic schema parses source="voice"
    req = AnswerRequest(
        question_id="voice-q-1",
        field_name="address",
        answer="New York, USA",
        source="voice",
    )
    assert req.source == "voice"


def test_focused_regression_generate_then_submit_answer():
    """
    Focused regression test:
    1. Calls question-generation logic for a document/form.
    2. Gets the generated question_id.
    3. Submits an answer using that exact question_id.
    4. Verifies HTTP 200 and status='accepted'.
    5. Verifies submitting an answer without generating questions returns 404.
    """
    # 1. Upload document and form
    doc_res = client.post(
        "/api/documents/upload",
        files={"file": ("passport.pdf", io.BytesIO(DUMMY_PDF), "application/pdf")},
    )
    doc_id = doc_res.json()["document_id"]

    form_res = client.post(
        "/api/forms/upload",
        files={"file": ("admission.pdf", io.BytesIO(DUMMY_PDF), "application/pdf")},
    )
    form_id = form_res.json()["form_id"]

    # 2. Get generated question_id via GET /questions
    q_res = client.get(f"/api/applications/{doc_id}/{form_id}/questions")
    assert q_res.status_code == 200
    questions = q_res.json()["questions"]
    assert len(questions) > 0

    target_q = questions[0]
    gen_qid = target_q["question_id"]
    gen_field = target_q["field_name"]

    # 3. Submit answer using that exact question_id
    payload = {
        "question_id": gen_qid,
        "field_name": gen_field,
        "answer": "Valid Answer Value",
        "source": "text",
    }
    ans_res = client.post(f"/api/applications/{doc_id}/{form_id}/answers", json=payload)

    # 4. Verify HTTP 200 and status="accepted"
    assert ans_res.status_code == 200
    assert ans_res.json()["question_id"] == gen_qid
    assert ans_res.json()["status"] == "accepted"

    # 5. Verify submitting an answer when state was cleared (like uvicorn restart before GET) returns 404
    clear_application_state()
    uninitialized_res = client.post(
        f"/api/applications/{doc_id}/{form_id}/answers",
        json=payload,
    )
    assert uninitialized_res.status_code == 404
    assert "not found" in uninitialized_res.json()["detail"].lower()

