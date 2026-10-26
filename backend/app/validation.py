"""Validate raw provider output before anything reaches the UI.

Recoverable problems (unknown intent, bad confidence, empty draft, risky wording)
become warnings and force human attention. Unrecoverable ones (not JSON, wrong
message_id) raise ProviderOutputError.
"""

import json
import re
import unicodedata

from app.models import CandidateMessage, Intent, MessageResult

MAX_DRAFT_CHARS = 700
MAX_TEXT_CHARS = 300  # provider-supplied reason / each warning
MAX_WARNINGS = 10

# Wording that states a recruitment outcome. A draft must never assert one unless a
# human has verified it, so any match is flagged for review. A word list cannot be
# complete; this is a safety net, and human review of every draft is the real control.
OUTCOME_CLAIMS = [
    r"short[\s-]?listed", r"hired", r"you(?:'ve| have)? passed", r"pleased to offer", r"offer you",
    r"extend(?:ing|ed)? (?:you )?an offer", r"through to the (?:next|final)",
    r"(?:been|were|was|are) (?:not )?selected", r"(?:un)?successful", r"next round",
    r"g[eo]t the job", r"congrat(?:s|ulations)", r"rejected", r"not (?:to )?proceed",
    r"moving forward with (?:you|your application|another candidate)",
]
_OUTCOME_RE = re.compile(r"\b(?:" + "|".join(OUTCOME_CLAIMS) + r")\b", re.IGNORECASE)
_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿­"))
_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'"})


def normalize_for_matching(text: str) -> str:
    """Fold look-alike characters so wording checks can't be dodged with Unicode tricks."""
    return unicodedata.normalize("NFKC", text).translate(_ZERO_WIDTH).translate(_APOSTROPHES)


def find_outcome_claim(draft: str, verified_status: str | None = None) -> str | None:
    text = normalize_for_matching(draft)
    if verified_status:
        # The recruiter supplied this status, so echoing it is not a fabricated claim.
        text = text.replace(normalize_for_matching(verified_status), " ")
    match = _OUTCOME_RE.search(text)
    return match.group(0) if match else None


def _clip(text: str) -> str:
    return text if len(text) <= MAX_TEXT_CHARS else text[: MAX_TEXT_CHARS - 1] + "…"


class ProviderOutputError(ValueError):
    pass


def parse_provider_output(raw: str, message: CandidateMessage, provider_name: str) -> MessageResult:
    try:
        data = json.loads(raw)
    # ValueError covers JSONDecodeError and int-digit-limit errors; RecursionError
    # covers deeply nested input.
    except (ValueError, TypeError, RecursionError) as exc:
        raise ProviderOutputError("output was not valid JSON") from exc
    if not isinstance(data, dict):
        raise ProviderOutputError("output was not a JSON object")

    warnings: list[str] = []
    returned_id = data.get("message_id")
    if returned_id is None:
        warnings.append("Provider did not echo the message_id; check the draft matches this message.")
    elif str(returned_id) != message.message_id:
        raise ProviderOutputError("output message_id does not match the input message")

    raw_warnings = data.get("warnings", [])
    if isinstance(raw_warnings, list):
        warnings.extend(_clip(str(w)) for w in raw_warnings[:MAX_WARNINGS] if str(w).strip())
    else:
        warnings.append("Provider warnings were not a list and were ignored.")

    try:
        intent = Intent(data.get("intent"))
    except ValueError:
        intent = Intent.OTHER_OR_UNCLEAR
        warnings.append(f"Provider returned an unknown intent ({str(data.get('intent'))[:40]!r}); "
                        "treated as other_or_unclear.")

    confidence = data.get("confidence")
    if confidence not in ("high", "medium", "low"):
        confidence = "low"
        warnings.append("Provider returned an invalid confidence; treated as low.")

    reason = data.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        reason = "No reason given by provider."
        warnings.append("Provider gave no classification reason.")

    draft = data.get("draft_reply")
    draft = draft.strip() if isinstance(draft, str) else ""
    if not draft:
        draft = None
        warnings.append("No draft could be generated; write a reply manually.")
    else:
        if len(draft) > MAX_DRAFT_CHARS:
            warnings.append("Draft is longer than expected; review carefully.")
        claim = find_outcome_claim(draft, message.application_status)
        if claim:
            warnings.append(f"Draft states a recruitment outcome ({claim!r}); "
                            "confirm it against verified information before approving.")

    needs_attention = (
        data.get("needs_human_attention") is True
        or bool(warnings)
        or confidence != "high"
        or intent == Intent.OTHER_OR_UNCLEAR
    )

    return MessageResult(
        message_id=message.message_id,
        intent=intent,
        confidence=confidence,
        reason=_clip(reason.strip()),
        draft_reply=draft,
        needs_human_attention=needs_attention,
        warnings=warnings[:MAX_WARNINGS],
        provider=provider_name,
    )
