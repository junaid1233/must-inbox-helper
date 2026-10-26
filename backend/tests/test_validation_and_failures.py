"""Invalid model output and provider failures must yield a flagged result, never a crash."""

import json

import pytest

from app.models import CandidateMessage, Intent
from app.pipeline import process_message
from app.providers.base import ProviderTimeout, ProviderUnavailable
from tests.fakes import RaisingProvider, StaticProvider

MSG = CandidateMessage(message_id="m7", text="Any update on my application?")


def good(**overrides):
    data = {"message_id": "m7", "intent": "application_status", "confidence": "high",
            "reason": "asked for update", "draft_reply": "Hello,\n\nThanks for checking in."}
    data.update(overrides)
    return json.dumps(data)


def assert_failed(result):
    assert result.message_id == "m7"
    assert result.intent == Intent.OTHER_OR_UNCLEAR
    assert result.confidence == "low"
    assert result.draft_reply is None
    assert result.needs_human_attention
    assert result.warnings


def test_well_formed_output_passes_through():
    result = process_message(MSG, StaticProvider(good()))
    assert result.intent == Intent.APPLICATION_STATUS
    assert result.draft_reply == "Hello,\n\nThanks for checking in."
    assert result.warnings == []
    assert result.needs_human_attention is False


@pytest.mark.parametrize("raw", [
    "not json at all",
    "",
    "```json\n{\"intent\": \"offer\"}\n```",
    "[1, 2, 3]",
    "null",
])
def test_malformed_output_becomes_flagged_failure(raw):
    assert_failed(process_message(MSG, StaticProvider(raw)))


def test_mismatched_message_id_is_rejected():
    result = process_message(MSG, StaticProvider(good(message_id="someone-else")))
    assert_failed(result)
    assert "message_id" in result.warnings[0]


def test_unknown_intent_is_coerced_to_unclear():
    result = process_message(MSG, StaticProvider(good(intent="urgent_vip")))
    assert result.intent == Intent.OTHER_OR_UNCLEAR
    assert result.needs_human_attention
    assert any("unknown intent" in w for w in result.warnings)


def test_invalid_confidence_becomes_low():
    result = process_message(MSG, StaticProvider(good(confidence=0.97)))
    assert result.confidence == "low"
    assert result.needs_human_attention


@pytest.mark.parametrize("draft", ["", "   ", None, 42])
def test_empty_or_non_string_draft_means_no_draft(draft):
    result = process_message(MSG, StaticProvider(good(draft_reply=draft)))
    assert result.draft_reply is None
    assert result.needs_human_attention
    assert any("No draft" in w for w in result.warnings)


@pytest.mark.parametrize("claim", [
    "Congratulations, you've been shortlisted!",
    "We are pleased to offer you the position.",
    "Unfortunately you were not selected.",
    "You passed the technical round and move to the next round.",
])
def test_outcome_claims_in_draft_are_flagged(claim):
    result = process_message(MSG, StaticProvider(good(draft_reply=claim)))
    assert result.needs_human_attention
    assert any("recruitment outcome" in w for w in result.warnings)


def test_overlong_draft_is_flagged():
    result = process_message(MSG, StaticProvider(good(draft_reply="Thanks. " * 200)))
    assert any("longer than expected" in w for w in result.warnings)


@pytest.mark.parametrize("exc, phrase", [
    (ProviderTimeout(), "timed out"),
    (ProviderUnavailable("rate limited"), "unavailable"),
    (RuntimeError("bug"), "failed unexpectedly"),
])
def test_provider_exceptions_become_flagged_failures(exc, phrase):
    result = process_message(MSG, RaisingProvider(exc))
    assert_failed(result)
    assert phrase in result.warnings[0]
