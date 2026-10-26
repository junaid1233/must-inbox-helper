"""Turn Pydantic validation errors into short, plain-English messages.

Keyed on the error *type* (stable), not Pydantic's English wording. Never
includes the submitted value, which may contain personal data.
"""

from typing import Any

FIELD_LABELS = {
    "message_id": "Message ID",
    "candidate": "Candidate",
    "text": "Message text",
    "received_at": "Received time",
    "application_status": "Application status",
    "context": "Context",
    "messages": "Messages",
    "csv": "CSV",
}


def friendly_message(error: dict[str, Any]) -> str:
    fields = [part for part in error.get("loc", ()) if isinstance(part, str) and part != "body"]
    field = fields[-1] if fields else ""
    label = FIELD_LABELS.get(field, field.replace("_", " ").capitalize() or "Request")
    kind = error.get("type", "")
    ctx = error.get("ctx") or {}

    if kind == "json_invalid":
        return "The request body is not valid JSON."
    if kind in ("model_attributes_type", "dict_type", "model_type") or (kind == "missing" and not field):
        return "The request must be a JSON object."
    if kind == "missing":
        return f"{label} is missing."
    if kind == "string_too_short":
        return f"{label} is empty." if ctx.get("min_length") == 1 else f"{label} is too short."
    if kind == "string_too_long":
        return f"{label} is longer than {ctx.get('max_length', 0):,} characters."
    if kind == "string_type":
        return f"{label} must be text."
    if kind == "too_short" and field == "messages":
        return "Add at least one message."
    if kind == "too_long" and field == "messages":
        return f"Too many messages: the limit is {ctx.get('max_length')} per batch."
    if kind == "list_type":
        return f"{label} must be a list."
    return f"{label}: {error.get('msg', 'is not valid')}."


def friendly_detail(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """FastAPI-shaped detail ({loc, msg, type}) without the echoed input."""
    return [{"loc": list(e.get("loc", ())), "msg": friendly_message(e), "type": e.get("type")} for e in errors]
