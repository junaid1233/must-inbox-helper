"""Classify and draft one message, never letting a provider failure crash the batch."""

import logging

from app.models import CandidateMessage, Intent, MessageResult
from app.providers.base import AIProvider, ProviderError, ProviderTimeout
from app.safety import find_injection_signals
from app.validation import ProviderOutputError, parse_provider_output

logger = logging.getLogger(__name__)


def _failed(message: CandidateMessage, provider: AIProvider, why: str) -> MessageResult:
    return MessageResult(
        message_id=message.message_id,
        intent=Intent.OTHER_OR_UNCLEAR,
        confidence="low",
        reason=f"Not classified: {why}",
        draft_reply=None,
        needs_human_attention=True,
        warnings=[f"{why} No draft was generated; write a reply manually."],
        provider=provider.name,
    )


INJECTION_WARNING = ("Message appears to contain instructions aimed at the system ({}). "
                     "They were treated as message content, not followed.")


def process_message(message: CandidateMessage, provider: AIProvider) -> MessageResult:
    result = _classify_and_draft(message, provider)
    signals = find_injection_signals(message.text) + find_injection_signals(message.context)
    if signals:
        logger.info("injection signals message_id=%s count=%d", message.message_id, len(signals))
        snippet = ", ".join(repr(s[:40]) for s in signals[:3])
        result.warnings.insert(0, INJECTION_WARNING.format(snippet))
        result.needs_human_attention = True
    return result


def _classify_and_draft(message: CandidateMessage, provider: AIProvider) -> MessageResult:
    # Log ids and error types only, never message text (it may contain PII).
    try:
        raw = provider.analyze(message)
    except ProviderTimeout:
        logger.warning("provider timeout message_id=%s", message.message_id)
        return _failed(message, provider, "The AI provider timed out.")
    except ProviderError as exc:
        logger.warning("provider error message_id=%s type=%s", message.message_id, type(exc).__name__)
        return _failed(message, provider, "The AI provider was unavailable.")
    except Exception as exc:  # a buggy provider must not take down the batch
        # No traceback: SDK errors can embed the request payload, i.e. the message text.
        logger.warning("unexpected provider failure message_id=%s type=%s",
                       message.message_id, type(exc).__name__)
        return _failed(message, provider, "The AI provider failed unexpectedly.")

    try:
        return parse_provider_output(raw, message, provider.name)
    except ProviderOutputError as exc:
        logger.warning("invalid provider output message_id=%s detail=%s", message.message_id, exc)
        return _failed(message, provider, f"The AI provider returned invalid output ({exc}).")
    except Exception as exc:
        logger.warning("output validation failed message_id=%s type=%s",
                       message.message_id, type(exc).__name__)
        return _failed(message, provider, "The AI provider's output could not be checked.")
