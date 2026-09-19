from app.services.form_service import process_documents
from app.schemas.application_schema import DocumentProcessingRequest


def test_process_documents_matches_contract_shape() -> None:
    response = process_documents(
        DocumentProcessingRequest(
            application_id="demo-001",
            form_id="scholarship-2026",
            document_ids=["aadhaar.pdf"],
        )
    )
    assert response.status == "success"
    assert response.application_id == "demo-001"
    assert response.fields["name"]["confidence"] == 0.98
