import json
from typing import Any


def to_json(value: Any) -> str:
    return json.dumps(value, default=str)
