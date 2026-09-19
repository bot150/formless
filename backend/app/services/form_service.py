from app.schemas.application_schema import ApplicationResponse, DocumentProcessingRequest
from app.schemas.form_schema import FormField, FormSchema

DEFAULT_FIELDS = [
    "name",
    "date_of_birth",
    "annual_income",
    "occupation",
    "bank_account",
    "hostel_status",
]

# Sample form: student_application
student_application = FormSchema(
    form_id="student_application",
    fields=[
        FormField(name="full_name", label="Full Name", type="text", required=True),
        FormField(name="date_of_birth", label="Date of Birth", type="date", required=True),
        FormField(name="email", label="Email", type="email", required=True),
        FormField(name="phone", label="Phone", type="phone", required=True),
        FormField(name="address", label="Address", type="text", required=True),
        FormField(name="student_id", label="Student ID", type="text", required=True),
    ],
)

FORMS_REGISTRY: dict[str, FormSchema] = {
    "student_application": student_application,
}


def get_form_schema(form_id: str) -> FormSchema | None:
    return FORMS_REGISTRY.get(form_id)


def process_documents(request: DocumentProcessingRequest) -> ApplicationResponse:
    fields = {
        "name": {"value": "Rahul Kumar", "confidence": 0.98, "source": "aadhaar"},
        "date_of_birth": {"value": "12/05/2005", "confidence": 0.97, "source": "aadhaar"},
        "annual_income": {"value": "200000", "confidence": 0.76, "source": "income_certificate"},
    }
    missing_fields = [field for field in DEFAULT_FIELDS if field not in fields]
    return ApplicationResponse(
        application_id=request.application_id,
        status="success",
        total_fields=len(DEFAULT_FIELDS),
        filled_fields=len(fields),
        missing_fields=missing_fields,
        fields=fields,
    )
