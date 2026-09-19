from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_student_application_schema():
    response = client.get("/api/forms/student_application")
    assert response.status_code == 200

    data = response.json()
    assert data["form_id"] == "student_application"
    assert isinstance(data["fields"], list)
    assert len(data["fields"]) == 6

    field_names = [f["name"] for f in data["fields"]]
    expected_fields = [
        "full_name",
        "date_of_birth",
        "email",
        "phone",
        "address",
        "student_id",
    ]
    assert field_names == expected_fields

    for field in data["fields"]:
        assert "name" in field
        assert "label" in field
        assert "type" in field
        assert "required" in field
        assert field["required"] is True


def test_get_nonexistent_form():
    response = client.get("/api/forms/unknown_form")
    assert response.status_code == 404
    assert response.json()["detail"] == "Form 'unknown_form' not found"
