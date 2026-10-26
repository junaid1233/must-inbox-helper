"""Process a batch of raw records with per-row validation.

Guarantees:
- Every input row appears exactly once: in `results` or in `errors`, by 1-based row.
- A bad row never stops the others.
- Every result has a unique message_id. A missing id gets a generated `auto-<row>`
  id with a warning; a repeated id keeps the first valid row and rejects the rest.
  An invalid row does not claim its id, so a later valid row with that id is kept.
- Unknown fields are ignored; they never trigger any action.
- Error text never echoes submitted values (they may contain PII).
"""

import re
from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from app.models import (
    MAX_BATCH,
    BatchMessageResult,
    BatchResponse,
    BatchSummary,
    CandidateMessage,
    RowError,
)
from app.grouping import group_results
from app.pipeline import process_message
from app.providers.base import AIProvider

__all__ = ["MAX_BATCH", "process_batch"]


def _clean_id(raw: Any) -> str | None:
    """Normalise a supplied id; '' means missing, None means unusable type."""
    if raw is None:
        return ""
    if isinstance(raw, bool) or not isinstance(raw, (str, int)):
        return None
    return str(raw).strip()


def _describe(exc: ValidationError) -> list[str]:
    lines = []
    for err in exc.errors(include_input=False, include_url=False):
        field = ".".join(str(part) for part in err["loc"])
        lines.append(f"{field}: {err['msg']}" if field else err["msg"])
    return lines


def _rows(rows: list[int]) -> str:
    return f"row {rows[0]}" if len(rows) == 1 else f"rows {', '.join(map(str, rows))}"


def _text_key(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def process_batch(
    records: list[Any],
    provider: AIProvider,
    row_problems: Mapping[int, list[str]] | None = None,
) -> BatchResponse:
    """`row_problems` lets an importer (e.g. CSV) report rows it could not even parse."""
    row_problems = row_problems or {}
    supplied_ids = {
        cid for rec in records if isinstance(rec, dict) and (cid := _clean_id(rec.get("message_id")))
    }
    errors: list[RowError] = []
    accepted: list[tuple[int, CandidateMessage, list[str]]] = []
    first_row_for_id: dict[str, int] = {}
    later_rows_for_id: dict[str, list[int]] = defaultdict(list)
    used_ids = set(supplied_ids)

    for row, record in enumerate(records, start=1):
        if row in row_problems:
            errors.append(RowError(row=row, message_id=None, errors=list(row_problems[row])))
            continue
        if not isinstance(record, dict):
            errors.append(RowError(row=row, message_id=None,
                                   errors=["Row is not an object with message fields."]))
            continue

        message_id = _clean_id(record.get("message_id"))
        if message_id is None:
            errors.append(RowError(row=row, message_id=None,
                                   errors=["message_id must be text or a whole number."]))
            continue

        notes: list[str] = []
        if not message_id:
            message_id = f"auto-{row}"
            suffix = 2
            while message_id in used_ids:
                message_id = f"auto-{row}-{suffix}"
                suffix += 1
            used_ids.add(message_id)
            notes.append(f"No message_id supplied; assigned {message_id}.")

        if message_id in first_row_for_id:
            first = first_row_for_id[message_id]
            later_rows_for_id[message_id].append(row)
            errors.append(RowError(row=row, message_id=message_id,
                                   errors=[f"Duplicate message_id (already used in row {first})."]))
            continue

        try:
            message = CandidateMessage(**{**record, "message_id": message_id})
        except ValidationError as exc:
            errors.append(RowError(row=row, message_id=message_id, errors=_describe(exc)))
            continue

        first_row_for_id[message_id] = row
        accepted.append((row, message, notes))

    rows_for_id = {mid: row for mid, row in first_row_for_id.items()}
    same_text: dict[str, list[str]] = defaultdict(list)
    for _, message, _ in accepted:
        same_text[_text_key(message.text)].append(message.message_id)

    results: list[BatchMessageResult] = []
    for row, message, notes in accepted:
        result = process_message(message, provider)
        extra = list(notes)
        if later := later_rows_for_id.get(message.message_id):
            extra.append(f"message_id also used by {_rows(later)} (rejected); "
                         "check they are not different messages.")
        twins = [mid for mid in same_text[_text_key(message.text)] if mid != message.message_id]
        if twins:
            extra.append(f"Possible duplicate: same text as {', '.join(twins)} "
                         f"({_rows([rows_for_id[t] for t in twins])}).")
        result.warnings = extra + result.warnings
        result.needs_human_attention = result.needs_human_attention or bool(extra)
        results.append(BatchMessageResult(**result.model_dump(), row=row))

    return BatchResponse(
        results=results,
        groups=group_results(results),
        errors=errors,
        summary=BatchSummary(received=len(records), processed=len(results), rejected=len(errors)),
    )
