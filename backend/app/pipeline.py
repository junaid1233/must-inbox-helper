"""Classify and draft one message, never letting a provider failure crash the batch."""

import logging

from app.models import CandidateMessage, Intent, MessageResult
from app.providers.base import AIProvider, ProviderError, ProviderTimeout
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


def process_message(message: CandidateMessage, provider: AIProvider) -> MessageResult:
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
