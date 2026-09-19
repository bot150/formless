from dataclasses import dataclass, field


@dataclass
class FormModel:
    form_id: str
    name: str
    fields: list[str] = field(default_factory=list)
