import io
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.utils.file_utils import DOCUMENTS_DIR, FORMS_DIR

client = TestClient(app)

DUMMY_PDF = b"%PDF-1.4 sample pdf binary data"
DUMMY_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
DUMMY_JPG = b"\xff\xd8\xff\xe0\x00\x10JFIF"


def test_successful_document_upload_pdf():
    file_bytes = io.BytesIO(DUMMY_PDF)
    response = client.post(
        "/api/documents/upload",
        files={"file": ("passport.pdf", file_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "document_id" in data
    assert data["filename"] == "passport.pdf"
    assert data["content_type"] == "application/pdf"

    # Verify file is saved in temp/documents/
    saved_file = DOCUMENTS_DIR / f"{data['document_id']}_passport.pdf"
    assert saved_file.exists()
    assert saved_file.read_bytes() == DUMMY_PDF


def test_successful_document_upload_png():
    file_bytes = io.BytesIO(DUMMY_PNG)
    response = client.post(
        "/api/documents/upload",
        files={"file": ("id_card.png", file_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content_type"] == "image/png"

    saved_file = DOCUMENTS_DIR / f"{data['document_id']}_id_card.png"
    assert saved_file.exists()


def test_successful_document_upload_jpg():
    file_bytes = io.BytesIO(DUMMY_JPG)
    response = client.post(
        "/api/documents/upload",
        files={"file": ("certificate.jpg", file_bytes, "image/jpeg")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content_type"] == "image/jpeg"

    saved_file = DOCUMENTS_DIR / f"{data['document_id']}_certificate.jpg"
    assert saved_file.exists()


def test_invalid_document_type():
    file_bytes = io.BytesIO(b"Some plain text")
    response = client.post(
        "/api/documents/upload",
        files={"file": ("notes.txt", file_bytes, "text/plain")},
    )
    assert response.status_code == 400


def test_successful_form_upload_pdf():
    file_bytes = io.BytesIO(DUMMY_PDF)
    response = client.post(
        "/api/forms/upload",
        files={"file": ("application_form.pdf", file_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "form_id" in data
    assert data["filename"] == "application_form.pdf"
    assert data["content_type"] == "application/pdf"

    # Verify file is saved in temp/forms/
    saved_file = FORMS_DIR / f"{data['form_id']}_application_form.pdf"
    assert saved_file.exists()
    assert saved_file.read_bytes() == DUMMY_PDF


def test_successful_form_upload_png():
    file_bytes = io.BytesIO(DUMMY_PNG)
    response = client.post(
        "/api/forms/upload",
        files={"file": ("form_scan.png", file_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content_type"] == "image/png"

    saved_file = FORMS_DIR / f"{data['form_id']}_form_scan.png"
    assert saved_file.exists()


def test_successful_form_upload_jpg():
    file_bytes = io.BytesIO(DUMMY_JPG)
    response = client.post(
        "/api/forms/upload",
        files={"file": ("form_photo.jpg", file_bytes, "image/jpeg")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content_type"] == "image/jpeg"

    saved_file = FORMS_DIR / f"{data['form_id']}_form_photo.jpg"
    assert saved_file.exists()


def test_invalid_form_type():
    file_bytes = io.BytesIO(b"executable content")
    response = client.post(
        "/api/forms/upload",
        files={"file": ("program.exe", file_bytes, "application/octet-stream")},
    )
    assert response.status_code == 400


def test_unique_document_ids_and_no_overwrite():
    content_1 = b"%PDF-1.4 user 1 doc content"
    content_2 = b"%PDF-1.4 user 2 doc content"

    resp1 = client.post(
        "/api/documents/upload",
        files={"file": ("shared_name.pdf", io.BytesIO(content_1), "application/pdf")},
    )
    resp2 = client.post(
        "/api/documents/upload",
        files={"file": ("shared_name.pdf", io.BytesIO(content_2), "application/pdf")},
    )

    data1 = resp1.json()
    data2 = resp2.json()

    assert data1["document_id"] != data2["document_id"]

    saved_1 = DOCUMENTS_DIR / f"{data1['document_id']}_shared_name.pdf"
    saved_2 = DOCUMENTS_DIR / f"{data2['document_id']}_shared_name.pdf"

    assert saved_1.exists()
    assert saved_2.exists()
    assert saved_1.read_bytes() == content_1
    assert saved_2.read_bytes() == content_2


def test_unique_form_ids_and_no_overwrite():
    content_1 = b"%PDF-1.4 form 1 content"
    content_2 = b"%PDF-1.4 form 2 content"

    resp1 = client.post(
        "/api/forms/upload",
        files={"file": ("shared_form.pdf", io.BytesIO(content_1), "application/pdf")},
    )
    resp2 = client.post(
        "/api/forms/upload",
        files={"file": ("shared_form.pdf", io.BytesIO(content_2), "application/pdf")},
    )

    data1 = resp1.json()
    data2 = resp2.json()

    assert data1["form_id"] != data2["form_id"]

    saved_1 = FORMS_DIR / f"{data1['form_id']}_shared_form.pdf"
    saved_2 = FORMS_DIR / f"{data2['form_id']}_shared_form.pdf"

    assert saved_1.exists()
    assert saved_2.exists()
    assert saved_1.read_bytes() == content_1
    assert saved_2.read_bytes() == content_2
