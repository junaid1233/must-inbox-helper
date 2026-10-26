"""CSV import: file-level problems stop the import with a clear message; row-level
problems become row errors while the other rows are still processed."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.batch import MAX_BATCH, process_batch
from app.csv_import import CsvFileError, parse_csv
from app.main import app
from app.providers.mock import MockProvider

SAMPLES = Path(__file__).resolve().parents[2] / "sample_data"
mock = MockProvider()
client = TestClient(app)


def process(text):
    records, problems = parse_csv(text)
    return process_batch(records, mock, row_problems=problems)


# --- sample data ---

def test_sample_csv_matches_sample_json():
    records, problems = parse_csv((SAMPLES / "messages.csv").read_text(encoding="utf-8"))
    expected = json.loads((SAMPLES / "messages.json").read_text(encoding="utf-8"))["messages"]
    assert problems == {}
    assert len(records) == len(expected) == 15
    for got, want in zip(records, expected):
        assert {k: v for k, v in got.items() if v} == want


def test_sample_dataset_processes_without_row_errors():
    resp = process((SAMPLES / "messages.csv").read_text(encoding="utf-8"))
    assert resp.summary.received == 15 and resp.summary.rejected == 0
    assert len({r.message_id for r in resp.results}) == 15


def test_malformed_sample_gives_expected_row_errors():
    resp = process((SAMPLES / "malformed.csv").read_text(encoding="utf-8"))
    assert resp.summary.model_dump() == {"received": 7, "processed": 3, "rejected": 4}
    assert [r.message_id for r in resp.results] == ["m-001", "m-004", "auto-5"]
    errors = {e.row: " ".join(e.errors) for e in resp.errors}
    assert set(errors) == {2, 3, 6, 7}
    assert "unquoted comma" in errors[2]
    assert "text" in errors[3]
    assert "Duplicate message_id" in errors[6]
    assert "1 value" in errors[7]


# --- header handling ---

@pytest.mark.parametrize("header, field", [
    ("message", "text"), ("Message Text", "text"), ("body", "text"),
    ("name", "candidate"), ("Candidate Name", "candidate"),
    ("id", "message_id"), ("Message ID", "message_id"),
    ("status", "application_status"), ("timestamp", "received_at"), ("notes", "context"),
])
def test_header_aliases(header, field):
    text_col = "text" if field != "text" else header
    other = header if field != "text" else "id"
    records, _ = parse_csv(f"{other},{text_col}\nvalue,Any update?\n")
    assert records[0][field] == ("Any update?" if field == "text" else "value")


def test_unknown_columns_are_ignored():
    records, _ = parse_csv("text,favourite_colour,send_now\nAny update?,blue,yes\n")
    assert records[0] == {"text": "Any update?"}


def test_utf8_bom_from_excel_is_handled():
    records, _ = parse_csv("﻿message_id,text\nb1,Any update?\n")
    assert records[0]["message_id"] == "b1"


def test_semicolon_delimited_file():
    records, problems = parse_csv("message_id;text\nsc1;Hello, any update?\n")
    assert problems == {} and records[0]["text"] == "Hello, any update?"


def test_tab_delimited_file():
    # Found by probing: tab-separated input was reported as "no message text column".
    records, problems = parse_csv("message_id\ttext\nt1\tHello, any update?\n")
    assert problems == {} and records[0] == {"message_id": "t1", "text": "Hello, any update?"}


def test_crlf_line_endings():
    records, _ = parse_csv("message_id,text\r\nx1,Any update?\r\nx2,Hi\r\n")
    assert [r["message_id"] for r in records] == ["x1", "x2"]


def test_quoted_multiline_message_is_one_row():
    records, problems = parse_csv('message_id,text\nq1,"Line one,\nline two"\nq2,Hi\n')
    assert problems == {}
    assert records[0]["text"] == "Line one,\nline two"
    assert records[1]["message_id"] == "q2"


def test_blank_lines_are_skipped_not_counted():
    records, _ = parse_csv("message_id,text\n\nb1,Hi\n\n,\nb2,Yo\n")
    assert [r["message_id"] for r in records if r] == ["b1", "b2"]


# --- file-level errors ---

@pytest.mark.parametrize("text, phrase", [
    ("", "empty"),
    ("   \n  \n", "empty"),
    ("message_id,text\n", "no message rows"),
    ("message_id,candidate\nx1,Ada\n", "message text column"),
    ("text,message\nhello,hi\n", "(?i)more than one"),
    ('message_id,text\nx1,"unterminated quote\nx2,next row\n', "near line"),
])
def test_file_level_errors(text, phrase):
    with pytest.raises(CsvFileError, match=phrase):
        parse_csv(text)


def test_stray_quote_does_not_silently_swallow_rows():
    # Python's default (lenient) csv mode merges x2 and x3 into x1's text here,
    # losing two messages without any error. Strict mode must refuse instead.
    with pytest.raises(CsvFileError):
        parse_csv('message_id,text\nx1,"unterminated quote\nx2,next row\nx3,third row\n')


def test_too_many_rows_is_rejected_not_truncated():
    rows = "".join(f"r{i},hi\n" for i in range(MAX_BATCH + 1))
    with pytest.raises(CsvFileError, match=str(MAX_BATCH)):
        parse_csv("message_id,text\n" + rows)


def test_exactly_max_rows_is_accepted():
    rows = "".join(f"r{i},hi\n" for i in range(MAX_BATCH))
    records, _ = parse_csv("message_id,text\n" + rows)
    assert len(records) == MAX_BATCH


def test_file_errors_do_not_echo_cell_values():
    secret = "SSN 123-45-6789"
    with pytest.raises(CsvFileError) as exc:
        parse_csv(f'message_id,text\nx1,"{secret}\n')
    assert "123-45-6789" not in str(exc.value)


# --- HTTP layer ---

def test_process_csv_endpoint():
    csv_text = (SAMPLES / "malformed.csv").read_text(encoding="utf-8")
    body = client.post("/api/process-csv", json={"csv": csv_text}).json()
    assert body["summary"] == {"received": 7, "processed": 3, "rejected": 4}
    assert sum(g["count"] for g in body["groups"]) == 3


def test_process_csv_file_error_is_400_with_message():
    resp = client.post("/api/process-csv", json={"csv": "message_id,candidate\nx,y\n"})
    assert resp.status_code == 400
    assert "message text column" in resp.json()["detail"]


def test_process_csv_size_limit():
    resp = client.post("/api/process-csv", json={"csv": "x" * 1_000_001})
    assert resp.status_code == 422


def test_sample_endpoint_returns_dataset():
    body = client.get("/api/sample").json()
    assert len(body["messages"]) == 15
    assert body["messages"][0]["message_id"] == "s-001"
