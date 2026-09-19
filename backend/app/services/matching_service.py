"""
Local Rule-Based Matching Service
NOTE: This is a deterministic rule-based matching service using normalized strings and alias dictionaries.
Confidence scores (1.0 for exact, 0.9 for alias) are rule-based weights, NOT AI probabilities.
No LLM or machine learning is used in this layer.
"""

from app.schemas.extraction_schema import DetectedForm, ExtractedDocument, ExtractedField
from app.schemas.matching_schema import MatchedField, MatchingResult, MissingField

ALIAS_GROUPS: list[set[str]] = [
    {"full_name", "name", "applicant_name", "student_name"},
    {"date_of_birth", "dob", "birth_date"},
    {"email", "email_address"},
    {"phone", "mobile", "phone_number", "mobile_number", "contact_number"},
    {"address", "residential_address", "permanent_address"},
    {"student_id", "registration_number", "roll_number", "id_number"},
]


def normalize_field_name(name: str) -> str:
    return name.strip().lower().replace("-", "_").replace(" ", "_")


def are_aliases(name1: str, name2: str) -> bool:
    norm1 = normalize_field_name(name1)
    norm2 = normalize_field_name(name2)
    if norm1 == norm2:
        return True
    for group in ALIAS_GROUPS:
        if norm1 in group and norm2 in group:
            return True
    return False


def match_fields(
    extracted_doc: ExtractedDocument,
    detected_form: DetectedForm,
) -> MatchingResult:
    """
    Compares extracted document information against detected empty form fields.
    Matches are deterministic:
    - Exact match: confidence = 1.0 (rule-based deterministic score)
    - Alias match: confidence = 0.9 (rule-based deterministic score)
    Unmatched form fields are classified as MissingField.
    """
    matched_fields: list[MatchedField] = []
    missing_fields: list[MissingField] = []

    # Map normalized extracted fields
    extracted_by_exact: dict[str, ExtractedField] = {}
    for ef in extracted_doc.fields:
        norm = normalize_field_name(ef.field_name)
        extracted_by_exact[norm] = ef

    for form_field in detected_form.fields:
        norm_form_name = normalize_field_name(form_field.field_name)

        # 1. Check for exact normalized match
        if norm_form_name in extracted_by_exact:
            match = extracted_by_exact[norm_form_name]
            matched_fields.append(
                MatchedField(
                    field_name=form_field.field_name,
                    form_label=form_field.label,
                    value=match.value,
                    source=match.source,
                    confidence=1.0,
                    status="matched",
                )
            )
            continue

        # 2. Check for alias match
        alias_match: ExtractedField | None = None
        for ext_norm, ef in extracted_by_exact.items():
            if are_aliases(norm_form_name, ext_norm):
                alias_match = ef
                break

        if alias_match:
            matched_fields.append(
                MatchedField(
                    field_name=form_field.field_name,
                    form_label=form_field.label,
                    value=alias_match.value,
                    source=alias_match.source,
                    confidence=0.9,
                    status="matched",
                )
            )
            continue

        # 3. If no match found, classify as missing
        missing_fields.append(
            MissingField(
                field_name=form_field.field_name,
                form_label=form_field.label,
                field_type=form_field.field_type,
                required=form_field.required,
            )
        )

    return MatchingResult(
        document_id=extracted_doc.document_id,
        form_id=detected_form.form_id,
        matched_fields=matched_fields,
        missing_fields=missing_fields,
    )
