from typing import Literal
from pydantic import BaseModel

FieldType = Literal[
    "text",
    "number",
    "date",
    "email",
    "phone",
    "boolean",
    "select",
]


class FormField(BaseModel):
    name: str
    label: str
    type: FieldType
    required: bool = True


class FormSchema(BaseModel):
    form_id: str
    fields: list[FormField]
