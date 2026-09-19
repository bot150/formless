import io
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.answer_schema import AnswerResponse
from app.services.application_state_service import clear_application_state

client = TestClient(app)

DUMMY_PDF = b"%PDF-1.4 sample pdf for voice submission"
DUMMY_WAV = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
DUMMY_MP3 = b"\xff\xfb\x90\x44\x00\x00\x00\x00"


@pytest.fixture(autouse=True)
def reset_state():
    clear_application_state()
    yield
    clear_application_state()


@pytest.fixture
def voice_setup():
    """Uploads document and form, generates questions, returns IDs and question set."""
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

    q_res = client.get(f"/api/applications/{doc_id}/{form_id}/questions")
    questions = q_res.json()["questions"]

    return doc_id, form_id, questions


def test_valid_voice_answer_address(voice_setup):
    doc_id, form_id, questions = voice_setup
    address_q = next(q for q in questions if q["field_name"] == "address")

    data = {
        "question_id": address_q["question_id"],
        "field_name": "address",
        "test_transcript": "Vijayawada, Andhra Pradesh",
    }
    files = {
        "audio": ("voice_recording.wav", io.BytesIO(DUMMY_WAV), "audio/wav"),
    }

    res = client.post(
        f"/api/applications/{doc_id}/{form_id}/voice-answer",
        data=data,
        files=files,
    )
    assert res.status_code == 200

    resp_data = res.json()
    assert resp_data["question_id"] == address_q["question_id"]
    assert resp_data["field_name"] == "address"
    assert resp_data["answer"] == "Vijayawada, Andhra Pradesh"
    assert resp_data["source"] == "voice"
    assert resp_data["status"] == "accepted"

    validated = AnswerResponse.model_validate(resp_data)
    assert validated.source == "voice"


def test_valid_voice_answer_student_id(voice_setup):
    doc_id, form_id, questions = voice_setup
    student_q = next(q for q in questions if q["field_name"] == "student_id")

    data = {
        "question_id": student_q["question_id"],
        "field_name": "student_id",
        "test_transcript": "STU-12345",
    }
    files = {
        "audio": ("recording.mp3", io.BytesIO(DUMMY_MP3), "audio/mpeg"),
    }

    res = client.post(
        f"/api/applications/{doc_id}/{form_id}/voice-answer",
        data=data,
        files=files,
    )
    assert res.status_code == 200

    resp_data = res.json()
    assert resp_data["question_id"] == student_q["question_id"]
    assert resp_data["field_name"] == "student_id"
    assert resp_data["answer"] == "STU-12345"
    assert resp_data["source"] == "voice"
    assert resp_data["status"] == "accepted"


def test_voice_answer_uses_same_validation_as_text(voice_setup):
    """
    Proves voice answers use the exact same validation logic as text answers:
    - Trims whitespace
    - Validates field constraints (e.g. empty answer is rejected)
    """
    doc_id, form_id, questions = voice_setup
    address_q = next(q for q in questions if q["field_name"] == "address")

    # 1. Whitespace trimming
    data = {
        "question_id": address_q["question_id"],
        "field_name": "address",
        "test_transcript": "   Guntur, Andhra Pradesh   ",
    }
    files = {
        "audio": ("answer.wav", io.BytesIO(DUMMY_WAV), "audio/wav"),
    }
    res = client.post(
        f"/api/applications/{doc_id}/{form_id}/voice-answer",
        data=data,
        files=files,
    )
    assert res.status_code == 200
    assert res.json()["answer"] == "Guntur, Andhra Pradesh"

    # Compare with text answer endpoint for exact parity:
    text_res = client.post(
        f"/api/applications/{doc_id}/{form_id}/answers",
        json={
            "question_id": address_q["question_id"],
            "field_name": "address",
            "answer": "   Guntur, Andhra Pradesh   ",
            "source": "text",
        },
    )
    assert text_res.status_code == 200
    assert text_res.json()["answer"] == res.json()["answer"]
    assert text_res.json()["status"] == res.json()["status"]
    assert text_res.json()["source"] == "text"
    assert res.json()["source"] == "voice"


def test_empty_transcript_rejection(voice_setup):
    doc_id, form_id, questions = voice_setup
    address_q = next(q for q in questions if q["field_name"] == "address")

    data = {
        "question_id": address_q["question_id"],
        "field_name": "address",
        "test_transcript": "   ",
    }
    files = {
        "audio": ("silence.wav", io.BytesIO(DUMMY_WAV), "audio/wav"),
    }
    res = client.post(
        f"/api/applications/{doc_id}/{form_id}/voice-answer",
        data=data,
        files=files,
    )
    assert res.status_code == 400
    assert "empty transcript" in res.json()["detail"].lower()


def test_invalid_question_id(voice_setup):
    doc_id, form_id, _ = voice_setup
    data = {
        "question_id": "00000000-0000-0000-0000-000000000000",
        "field_name": "address",
        "test_transcript": "Some Address",
    }
    files = {
        "audio": ("answer.wav", io.BytesIO(DUMMY_WAV), "audio/wav"),
    }
    res = client.post(
        f"/api/applications/{doc_id}/{form_id}/voice-answer",
        data=data,
        files=files,
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_wrong_field_name(voice_setup):
    doc_id, form_id, questions = voice_setup
    address_q = next(q for q in questions if q["field_name"] == "address")

    data = {
        "question_id": address_q["question_id"],
        "field_name": "wrong_field_name",
        "test_transcript": "Some Address",
    }
    files = {
        "audio": ("answer.wav", io.BytesIO(DUMMY_WAV), "audio/wav"),
    }
    res = client.post(
        f"/api/applications/{doc_id}/{form_id}/voice-answer",
        data=data,
        files=files,
    )
    assert res.status_code == 400
    assert "does not match" in res.json()["detail"].lower()


def test_document_not_found(voice_setup):
    _, form_id, questions = voice_setup
    address_q = next(q for q in questions if q["field_name"] == "address")

    data = {
        "question_id": address_q["question_id"],
        "field_name": "address",
        "test_transcript": "Some Address",
    }
    files = {
        "audio": ("answer.wav", io.BytesIO(DUMMY_WAV), "audio/wav"),
    }
    res = client.post(
        f"/api/applications/nonexistent-doc/{form_id}/voice-answer",
        data=data,
        files=files,
    )
    assert res.status_code == 404
    assert "document" in res.json()["detail"].lower()


def test_form_not_found(voice_setup):
    doc_id, _, questions = voice_setup
    address_q = next(q for q in questions if q["field_name"] == "address")

    data = {
        "question_id": address_q["question_id"],
        "field_name": "address",
        "test_transcript": "Some Address",
    }
    files = {
        "audio": ("answer.wav", io.BytesIO(DUMMY_WAV), "audio/wav"),
    }
    res = client.post(
        f"/api/applications/{doc_id}/nonexistent-form/voice-answer",
        data=data,
        files=files,
    )
    assert res.status_code == 404
    assert "form" in res.json()["detail"].lower()


def test_unsupported_audio_format(voice_setup):
    doc_id, form_id, questions = voice_setup
    address_q = next(q for q in questions if q["field_name"] == "address")

    data = {
        "question_id": address_q["question_id"],
        "field_name": "address",
        "test_transcript": "Some Address",
    }
    files = {
        "audio": ("answer.txt", io.BytesIO(b"not audio"), "text/plain"),
    }
    res = client.post(
        f"/api/applications/{doc_id}/{form_id}/voice-answer",
        data=data,
        files=files,
    )
    assert res.status_code == 400
    assert "unsupported audio format" in res.json()["detail"].lower()


def test_browser_voice_transcript_flow_via_answers_endpoint(voice_setup):
    """
    Verifies that speech-to-text transcript generated by browser Speech Recognition
    is submitted directly to the existing /answers endpoint with source='voice',
    validates identically to text, and returns AnswerResponse with source='voice'.
    """
    doc_id, form_id, questions = voice_setup
    address_q = next(q for q in questions if q["field_name"] == "address")

    # Speech recognition output from browser
    recognized_transcript = "Vijayawada, Andhra Pradesh"

    payload = {
        "question_id": address_q["question_id"],
        "field_name": "address",
        "answer": recognized_transcript,
        "source": "voice",
    }

    res = client.post(f"/api/applications/{doc_id}/{form_id}/answers", json=payload)
    assert res.status_code == 200

    data = res.json()
    assert data["question_id"] == address_q["question_id"]
    assert data["field_name"] == "address"
    assert data["answer"] == "Vijayawada, Andhra Pradesh"
    assert data["source"] == "voice"
    assert data["status"] == "accepted"


def test_voice_html_page_served():
    """Verifies that the interactive voice UI is served at GET /voice."""
    res = client.get("/voice")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "Formless Voice Interaction" in res.text
    assert "Start Speaking" in res.text
    assert "Read Question" in res.text

