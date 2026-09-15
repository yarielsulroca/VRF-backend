from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


def _value(value):
    if is_dataclass(value) and not isinstance(value, type):
        return dump(value)
    if hasattr(value, "value") and not isinstance(value, (str, int, float, bool)):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_value(v) for v in value]
    return value


def dump(item) -> dict:
    data = asdict(item) if is_dataclass(item) else dict(item)
    out = {key: _value(value) for key, value in data.items()}
    out.pop("password_hash", None)
    return out
