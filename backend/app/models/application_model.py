from dataclasses import dataclass, field


@dataclass
class ApplicationModel:
    application_id: str
    form_id: str
    answers: dict[str, object] = field(default_factory=dict)
