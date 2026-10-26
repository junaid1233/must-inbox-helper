"""Regression tests for issues found by the independent code review on 2026-10-26 (Day 1).

Each test was written to fail against the pre-fix code; see logs/day-1.md.
"""

import json

import pytest

from app.models import CandidateMessage, Intent
from app.pipeline import process_message
from app.providers.mock import MockProvider
from tests.fakes import StaticProvider

MSG = CandidateMessage(message_id="m7", text="Any update on my application?")
mock = MockProvider()


def good(**overrides):
    data = {"message_id": "m7", "intent": "application_status", "confidence": "high",
            "reason": "asked for update", "draft_reply": "Hello,\n\nThanks for checking in."}
    data.update(overrides)
    return json.dumps(data)


def classify(text, **fields):
    return process_message(CandidateMessage(message_id="r1", text=text, **fields), mock)


# Finding 1: json.loads can raise errors other than JSONDecodeError.
@pytest.mark.parametrize("raw", ["[" * 100000, "1" * 5000], ids=["deep_nesting", "huge_integer"])
def test_pathological_json_does_not_escape_pipeline(raw):
    result = process_message(MSG, StaticProvider(raw))
    assert result.draft_reply is None
    assert result.needs_human_attention


# Finding 2: outcome wording that slipped past the claim check.
@pytest.mark.parametrize("draft", [
    "You have been selected for the role.",
    "We'd like to offer you the job.",
    "We have decided not to proceed.",
    "Your application was successful.",
    "You've been rejected.",
    "Congrats!",
    "You are short listed.",
    "You’ve passed the assessment.",  # curly apostrophe
    "You are short​listed.",          # zero-width space
    "We are moving forward with you.",
    # Found afterwards by the reviewer's probe script:
    "Great news, you are through to the final interview.",
    "We will be extending an offer.",
])
def test_more_outcome_wording_is_flagged(draft):
    result = process_message(MSG, StaticProvider(good(draft_reply=draft)))
    assert result.needs_human_attention
    assert any("recruitment outcome" in w for w in result.warnings), draft


@pytest.mark.parametrize("draft", [
    "Hello,\n\nThanks for checking in. I'll get back to you soon.",
    "Thanks for applying. Could you share a few times that work for you?",
    "I'll check with the team on next steps.",
])
def test_neutral_drafts_are_not_flagged_as_outcomes(draft):
    result = process_message(MSG, StaticProvider(good(draft_reply=draft)))
    assert not any("recruitment outcome" in w for w in result.warnings)


# Finding 3: a provider that omits message_id must not pass silently.
def test_missing_message_id_is_flagged():
    data = json.loads(good())
    del data["message_id"]
    result = process_message(MSG, StaticProvider(json.dumps(data)))
    assert result.message_id == "m7"
    assert result.needs_human_attention
    assert any("message_id" in w for w in result.warnings)


# Finding 4: one phrase must not count as two keyword hits.
@pytest.mark.parametrize("text", [
    "What is the pay range?",
    "I'd like to re-schedule.",
    "I attached my resume.",
])
def test_overlapping_keywords_count_once(text):
    assert classify(text).confidence != "high"


# Finding 5: inflected words and common phrasings.
@pytest.mark.parametrize("text, intent", [
    ("I'm withdrawing my application.", Intent.WITHDRAWAL),
    ("I accepted the offer, what happens next?", Intent.OFFER),
    ("What is the status of my application for the position?", Intent.APPLICATION_STATUS),
    # Day 2 Task 2 probe: same trailing-\b bug as "withdrawing".
    ("Just checking where my application stands.", Intent.APPLICATION_STATUS),
])
def test_common_phrasings_classify(text, intent):
    assert classify(text).intent == intent


def test_withdrawal_draft_does_not_confirm_a_withdrawal():
    draft = classify("Should I withdraw my application or wait?").draft_reply.lower()
    assert "wish you all the best" not in draft


# Finding 6: a recruiter-supplied status must not trip the outcome warning.
def test_supplied_status_echo_is_not_flagged_as_fabricated():
    result = classify("Any update on my application status?", application_status="Shortlisted")
    assert "Shortlisted" in result.draft_reply
    assert not any("recruitment outcome" in w for w in result.warnings)


# Finding 8: provider-supplied text shown in the UI is bounded.
def test_provider_reason_and_warnings_are_truncated():
    raw = good(reason="x" * 5000, warnings=["w" * 5000] * 50)
    result = process_message(MSG, StaticProvider(raw))
    assert len(result.reason) <= 300
    assert len(result.warnings) <= 10
    assert all(len(w) <= 300 for w in result.warnings)


# Finding 9: the name allow-list must not include × or ÷.
def test_name_with_math_symbols_is_not_echoed():
    result = classify("Any update on my application?", candidate="A×B")
    assert result.draft_reply.startswith("Hello,")
