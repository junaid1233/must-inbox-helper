"""Batch processing: per-row validation, identity preservation, duplicates.

Core invariant: every input row appears exactly once, either in `results` or in
`errors`, identified by its 1-based row number.
"""

import pytest
from fastapi.testclient import TestClient

from app.batch import MAX_BATCH, process_batch
from app.main import app
from app.providers.mock import MockProvider
from tests.fakes import RaisingProvider
from app.providers.base import ProviderTimeout

mock = MockProvider()
client = TestClient(app)


def rows_accounted_for(response, n):
    seen = [r.row for r in response.results] + [e.row for e in response.errors]
    assert sorted(seen) == list(range(1, n + 1)), "every row exactly once"
    assert response.summary.received == n
    assert response.summary.processed == len(response.results)
    assert response.summary.rejected == len(response.errors)


def test_valid_batch_keeps_order_and_ids():
    records = [
        {"message_id": "a", "text": "Any update on my application status?"},
        {"message_id": "b", "text": "Could we reschedule my interview?"},
        {"message_id": "c", "text": "What is the salary range?"},
    ]
    resp = process_batch(records, mock)
    rows_accounted_for(resp, 3)
    assert [r.message_id for r in resp.results] == ["a", "b", "c"]
    assert [r.row for r in resp.results] == [1, 2, 3]
    assert resp.errors == []


def test_mixed_valid_and_invalid_rows():
    records = [
        {"message_id": "ok-1", "text": "Any update?"},
        {"message_id": "bad-1", "text": "   "},
        "not an object",
        {"message_id": "ok-2", "text": "I'd like to withdraw my application."},
        {"message_id": "bad-2", "text": "x" * 6000},
        None,
    ]
    resp = process_batch(records, mock)
    rows_accounted_for(resp, 6)
    assert [r.message_id for r in resp.results] == ["ok-1", "ok-2"]
    assert [e.row for e in resp.errors] == [2, 3, 5, 6]
    assert resp.errors[0].message_id == "bad-1"
    assert any("text" in m for m in resp.errors[0].errors)
    assert resp.errors[1].message_id is None


def test_results_carry_the_validated_message_for_review():
    resp = process_batch([{"text": "  Any update?  ", "candidate": "Ana", "context": ""}], mock)
    message = resp.results[0].message
    assert message.message_id == resp.results[0].message_id == "auto-1"
    assert message.text == "Any update?"
    assert message.candidate == "Ana"
    assert message.context is None


def test_errors_do_not_echo_submitted_values():
    secret = "my SSN is 123-45-6789 " + "y" * 6000
    resp = process_batch([{"message_id": "p1", "text": secret}], mock)
    joined = " ".join(resp.errors[0].errors)
    assert "123-45-6789" not in joined


@pytest.mark.parametrize("missing", [{}, {"message_id": ""}, {"message_id": "   "}, {"message_id": None}])
def test_missing_message_id_gets_unique_generated_id(missing):
    records = [{"text": "Any update?", **missing}, {"text": "Could we reschedule?"}]
    resp = process_batch(records, mock)
    rows_accounted_for(resp, 2)
    ids = [r.message_id for r in resp.results]
    assert ids == ["auto-1", "auto-2"]
    for r in resp.results:
        assert r.needs_human_attention
        assert any("No message_id" in w for w in r.warnings)


def test_generated_id_never_collides_with_supplied_id():
    records = [{"message_id": "auto-2", "text": "Any update?"}, {"text": "Hello there"}]
    resp = process_batch(records, mock)
    ids = [r.message_id for r in resp.results]
    assert len(set(ids)) == 2
    assert ids[0] == "auto-2"


def test_numeric_message_id_is_accepted_as_string():
    resp = process_batch([{"message_id": 42, "text": "Any update?"}], mock)
    assert resp.results[0].message_id == "42"


def test_duplicate_message_id_keeps_first_and_rejects_later():
    records = [
        {"message_id": "dup", "text": "Any update on my application?"},
        {"message_id": "other", "text": "Could we reschedule?"},
        {"message_id": "dup", "text": "A completely different message"},
    ]
    resp = process_batch(records, mock)
    rows_accounted_for(resp, 3)
    assert [r.message_id for r in resp.results] == ["dup", "other"]
    assert resp.errors[0].row == 3
    assert "row 1" in resp.errors[0].errors[0]
    first = resp.results[0]
    assert first.needs_human_attention
    assert any("row 3" in w for w in first.warnings)


def test_duplicate_id_check_ignores_surrounding_whitespace():
    records = [{"message_id": "m1", "text": "Hi"}, {"message_id": " m1 ", "text": "Hello"}]
    resp = process_batch(records, mock)
    assert len(resp.results) == 1 and len(resp.errors) == 1


def test_same_text_under_different_ids_is_processed_and_warned():
    records = [
        {"message_id": "x1", "text": "Any update on my application?"},
        {"message_id": "x2", "text": "  any UPDATE on my   application? "},
        {"message_id": "x3", "text": "Could we reschedule?"},
    ]
    resp = process_batch(records, mock)
    rows_accounted_for(resp, 3)
    by_id = {r.message_id: r for r in resp.results}
    assert any("x2" in w for w in by_id["x1"].warnings)
    assert any("x1" in w for w in by_id["x2"].warnings)
    assert by_id["x1"].needs_human_attention and by_id["x2"].needs_human_attention
    assert not any("duplicate" in w.lower() for w in by_id["x3"].warnings)
    assert any("(row 2)" in w for w in by_id["x1"].warnings)


def test_three_way_duplicate_text_uses_plural_rows():
    records = [{"message_id": i, "text": "Any update?"} for i in "pqr"]
    first = process_batch(records, mock).results[0]
    assert any("(rows 2, 3)" in w for w in first.warnings)


def test_invalid_row_does_not_claim_its_id():
    records = [{"message_id": "d", "text": ""}, {"message_id": "d", "text": "Any update?"}]
    resp = process_batch(records, mock)
    assert [r.row for r in resp.results] == [2]
    assert [e.row for e in resp.errors] == [1]


def test_unknown_fields_are_ignored():
    resp = process_batch([{"message_id": "e", "text": "hi", "send_now": True}], mock)
    assert resp.results[0].message_id == "e"
    assert "send_now" not in resp.results[0].model_dump()


def test_provider_failure_on_one_row_does_not_stop_batch():
    resp = process_batch([{"message_id": "t1", "text": "hi"}, {"message_id": "t2", "text": "yo"}],
                         RaisingProvider(ProviderTimeout()))
    rows_accounted_for(resp, 2)
    assert all(r.draft_reply is None and r.needs_human_attention for r in resp.results)


def test_large_mixed_batch_invariant():
    records = []
    for i in range(MAX_BATCH):
        kind = i % 5
        if kind == 0:
            records.append({"message_id": f"m{i}", "text": f"Any update on application {i}?"})
        elif kind == 1:
            records.append({"message_id": f"m{i}", "text": ""})
        elif kind == 2:
            records.append({"text": f"Could we reschedule interview {i}?"})
        elif kind == 3:
            records.append({"message_id": "m0", "text": "duplicate id"})
        else:
            records.append(12345)
    resp = process_batch(records, mock)
    rows_accounted_for(resp, MAX_BATCH)
    ids = [r.message_id for r in resp.results]
    assert len(ids) == len(set(ids)), "no id appears twice in results"


# --- HTTP layer ---

def test_batch_endpoint_returns_results_errors_and_summary():
    resp = client.post("/api/process-batch", json={"messages": [
        {"message_id": "h1", "text": "Any update?"},
        {"message_id": "h2", "text": ""},
    ]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"] == {"received": 2, "processed": 1, "rejected": 1}
    assert body["results"][0]["message_id"] == "h1"
    assert body["results"][0]["row"] == 1
    assert body["errors"][0]["row"] == 2


@pytest.mark.parametrize("payload", [
    {"messages": []},
    {"messages": [{"message_id": "x", "text": "hi"}] * (MAX_BATCH + 1)},
    {"messages": "not a list"},
    {},
    [],
])
def test_batch_endpoint_rejects_bad_envelopes(payload):
    assert client.post("/api/process-batch", json=payload).status_code == 422
