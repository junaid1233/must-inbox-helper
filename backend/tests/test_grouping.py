"""Grouping by intent.

Rules: each processed message is in exactly one group; groups list message ids
(not copies of results); counts add up to `summary.processed`; empty groups are
left out; groups follow the fixed Intent order with other_or_unclear last.
Rejected rows are not grouped; they stay in `errors`.
"""

from fastapi.testclient import TestClient

from app.batch import process_batch
from app.grouping import group_results
from app.main import app
from app.models import Intent
from app.providers.base import ProviderUnavailable
from app.providers.mock import MockProvider
from tests.fakes import RaisingProvider

mock = MockProvider()

RECORDS = [
    {"message_id": "s1", "text": "Any update on my application status?"},
    {"message_id": "r1", "text": "Could we reschedule my interview to next week?"},
    {"message_id": "s2", "text": "Is there any update? Still waiting to hear back."},
    {"message_id": "u1", "text": "Hmm, okay."},
    {"message_id": "w1", "text": "I'd like to withdraw my application."},
    {"message_id": "bad", "text": ""},
    {"message_id": "s3", "text": "What's the status of my application?"},
]


def test_each_processed_message_in_exactly_one_group():
    resp = process_batch(RECORDS, mock)
    grouped = [mid for g in resp.groups for mid in g.message_ids]
    assert sorted(grouped) == sorted(r.message_id for r in resp.results)
    assert len(grouped) == len(set(grouped))
    assert sum(g.count for g in resp.groups) == resp.summary.processed


def test_groups_follow_intent_order_and_skip_empty():
    resp = process_batch(RECORDS, mock)
    intents = [g.intent for g in resp.groups]
    order = list(Intent)
    assert intents == sorted(intents, key=order.index)
    assert intents[-1] == Intent.OTHER_OR_UNCLEAR
    assert all(g.count > 0 for g in resp.groups)
    assert Intent.OFFER not in intents


def test_group_contents_counts_and_labels():
    resp = process_batch(RECORDS, mock)
    by_intent = {g.intent: g for g in resp.groups}
    status = by_intent[Intent.APPLICATION_STATUS]
    assert status.message_ids == ["s1", "s2", "s3"]  # input order kept
    assert status.count == 3
    assert status.label == "Application status inquiry"
    assert by_intent[Intent.INTERVIEW_SCHEDULING].message_ids == ["r1"]
    assert by_intent[Intent.WITHDRAWAL].message_ids == ["w1"]
    assert by_intent[Intent.OTHER_OR_UNCLEAR].message_ids == ["u1"]


def test_rejected_rows_are_not_grouped():
    resp = process_batch(RECORDS, mock)
    assert "bad" not in [mid for g in resp.groups for mid in g.message_ids]
    assert [e.message_id for e in resp.errors] == ["bad"]


def test_attention_count_per_group():
    resp = process_batch(RECORDS, mock)
    for group in resp.groups:
        members = [r for r in resp.results if r.message_id in group.message_ids]
        assert group.needs_attention_count == sum(r.needs_human_attention for r in members)


def test_provider_failures_land_in_unclear_group():
    resp = process_batch(RECORDS[:2], RaisingProvider(ProviderUnavailable()))
    assert [g.intent for g in resp.groups] == [Intent.OTHER_OR_UNCLEAR]
    assert resp.groups[0].count == 2


def test_empty_results_give_no_groups():
    assert group_results([]) == []


def test_batch_endpoint_includes_groups():
    body = TestClient(app).post("/api/process-batch", json={"messages": RECORDS}).json()
    assert {"intent", "label", "count", "needs_attention_count", "message_ids"} == set(body["groups"][0])
    assert sum(g["count"] for g in body["groups"]) == body["summary"]["processed"]
