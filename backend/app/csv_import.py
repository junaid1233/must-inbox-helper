"""Parse CSV text into batch records.

File-level problems (empty file, no text column, broken quoting, too many rows)
raise CsvFileError and stop the import. Row-level problems (wrong number of
values) are returned per row so the other rows can still be processed.
Error messages never include cell values.
"""

import csv
import io
import re

from app.models import MAX_BATCH

# Normalised header name -> CandidateMessage field. Unknown columns are ignored.
HEADER_ALIASES = {
    "message_id": "message_id", "id": "message_id", "msg_id": "message_id",
    "candidate": "candidate", "name": "candidate", "candidate_name": "candidate",
    "candidate_id": "candidate",
    "text": "text", "message": "text", "message_text": "text", "body": "text",
    "received_at": "received_at", "received": "received_at", "timestamp": "received_at",
    "date": "received_at",
    "application_status": "application_status", "status": "application_status",
    "context": "context", "notes": "context", "conversation_context": "context",
}
TEXT_HEADERS = sorted(name for name, field in HEADER_ALIASES.items() if field == "text")


class CsvFileError(ValueError):
    pass


def _normalise(header: str) -> str:
    return re.sub(r"[\s\-]+", "_", header.strip().lower())


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def parse_csv(text: str) -> tuple[list[dict | None], dict[int, list[str]]]:
    """Return (records, row_problems). A record is None where its row has a problem."""
    text = text.lstrip("﻿")
    if not text.strip():
        raise CsvFileError("The CSV file is empty.")

    first_line = text.lstrip().splitlines()[0]
    # Comma by default; semicolon (European Excel) or tab (pasted from a spreadsheet)
    # when the header clearly uses one instead.
    delimiter = max([",", ";", "\t"], key=first_line.count)
    # strict=True makes a stray quote an error instead of silently merging rows.
    reader = csv.reader(io.StringIO(text.lstrip(), newline=""), delimiter=delimiter, strict=True)

    try:
        header = next(reader)
        fields = [HEADER_ALIASES.get(_normalise(h)) for h in header]
        mapped = [f for f in fields if f]
        repeated = sorted({f for f in mapped if mapped.count(f) > 1})
        if repeated:
            raise CsvFileError(f"More than one column maps to {', '.join(repeated)}; keep only one.")
        if "text" not in mapped:
            raise CsvFileError("The CSV has no message text column "
                               f"(expected a header such as: {', '.join(TEXT_HEADERS)}).")

        records: list[dict | None] = []
        problems: dict[int, list[str]] = {}
        for values in reader:
            if not any(v.strip() for v in values):
                continue  # blank line, not a record
            if len(records) >= MAX_BATCH:
                raise CsvFileError(f"The CSV has more than {MAX_BATCH} messages. "
                                   f"Split it into files of at most {MAX_BATCH} rows.")
            row = len(records) + 1
            if len(values) != len(header):
                hint = " Is there an unquoted comma in the message text?" if len(values) > len(header) else ""
                problems[row] = [f"Line {reader.line_num} has {_plural(len(values), 'value')} "
                                 f"but the header has {len(header)}.{hint}"]
                records.append(None)
                continue
            records.append({f: v for f, v in zip(fields, values) if f})
    except csv.Error as exc:
        # csv.Error messages describe the problem, not the cell contents.
        raise CsvFileError(f"Could not read the CSV near line {reader.line_num}: {exc}.") from exc

    if not records:
        raise CsvFileError("The CSV has a header but no message rows.")
    return records, problems
