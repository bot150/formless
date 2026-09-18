# Formless API Contract

## 1. Process Documents

POST /api/process-documents

### Request

{
  "application_id": "demo-001",
  "form_id": "scholarship-2026",
  "document_ids": [
    "aadhaar.pdf",
    "income_certificate.pdf",
    "marksheet.pdf"
  ]
}

### Response

{
  "application_id": "demo-001",
  "status": "success",
  "total_fields": 25,
  "filled_fields": 18,
  "missing_fields": [
    "occupation",
    "bank_account",
    "hostel_status"
  ],
  "fields": {
    "name": {
      "value": "Rahul Kumar",
      "confidence": 0.98,
      "source": "aadhaar"
    },
    "date_of_birth": {
      "value": "12/05/2005",
      "confidence": 0.97,
      "source": "aadhaar"
    },
    "annual_income": {
      "value": "200000",
      "confidence": 0.76,
      "source": "income_certificate"
    }
  }
}