"""Deterministic keyword-rule provider for demo mode and tests.

No network, no randomness: the same message always gives the same output.
It is deliberately simple and will misread paraphrases, sarcasm and most
non-English text; that limitation is documented rather than hidden.

Confidence bands (a heuristic, not a probability):
- high:   one intent matched at least 2 keyword rules and no other intent matched
- medium: one intent clearly ahead, but with a single hit or competing matches
- low:    no match, or a tie between intents (classified as other_or_unclear)
"""

import json
import re

from app.models import CandidateMessage, Intent
from app.providers.base import AIProvider

KEYWORDS: dict[Intent, list[str]] = {
    Intent.APPLICATION_STATUS: [
        r"status", r"any update", r"an update", r"hear(d)? back", r"where (i|my application) stand(s|ing)?",
        r"progress of my application", r"still under review", r"been a while",
    ],
    Intent.INTERVIEW_SCHEDULING: [
        r"re-?schedule", r"move (my|the) interview", r"schedule", r"availability",
        r"time slot", r"postpone", r"different (time|day|date)", r"change the (time|date)",
        r"can't make (it|the interview)", r"cannot make (it|the interview)",
    ],
    Intent.INTERVIEW_FOLLOW_UP: [
        r"after (my|the) interview", r"following up on (my|the) interview",
        r"interview (yesterday|last week|on (monday|tuesday|wednesday|thursday|friday))",
        r"feedback", r"thank you for the interview", r"thanks for the interview",
    ],
    # Bare "role"/"position" also appear as context ("I applied for the X role"),
    # so only question-like phrasings count.
    Intent.ROLE_INQUIRY: [
        r"(about|is|does) (the|this) (role|position)", r"(role|position) (involve|require|include)\w*",
        r"job description", r"responsibilit(y|ies)", r"remote",
        r"requirements", r"opening", r"vacanc(y|ies)", r"tech stack", r"team size",
    ],
    Intent.APPLICATION_SUBMISSION: [
        r"submitted", r"just applied", r"received my application", r"confirm receipt",
        r"did you (get|receive)", r"attached (my )?(resume|cv)", r"resume", r"cv",
    ],
    Intent.COMPENSATION: [
        r"salary", r"compensation", r"pay", r"pay range", r"benefits", r"equity", r"bonus",
    ],
    Intent.OFFER: [
        r"offer letter", r"the offer", r"your offer", r"start date", r"accept(ed|ing)? the offer",
        r"negotiat(e|ion)",
    ],
    Intent.WITHDRAWAL: [
        r"withdraw\w*", r"no longer interested", r"cancel my application", r"accepted another",
        r"remove my application", r"pull out",
    ],
    Intent.NETWORKING: [
        r"connect", r"linkedin", r"coffee", r"networking", r"introduce myself", r"referral",
    ],
}

_COMPILED = {
    intent: [re.compile(rf"\b{pattern}\b", re.IGNORECASE) for pattern in patterns]
    for intent, patterns in KEYWORDS.items()
}

DRAFTS: dict[Intent, str] = {
    Intent.APPLICATION_STATUS: (
        "Thank you for checking in about your application. "
        "I'll look into where things stand and get back to you as soon as I can."
    ),
    Intent.INTERVIEW_SCHEDULING: (
        "Thanks for letting us know. Could you share two or three times that work for you? "
        "I'll check what we can arrange."
    ),
    Intent.INTERVIEW_FOLLOW_UP: (
        "Thank you for following up after your interview. "
        "I'll check with the team on next steps and get back to you."
    ),
    Intent.ROLE_INQUIRY: (
        "Thanks for your interest. Could you let me know which position you're asking about "
        "and what you'd like to know, so I can point you to the right details?"
    ),
    Intent.APPLICATION_SUBMISSION: (
        "Thanks for getting in touch about your application. "
        "I'll check that we have it on file and confirm back to you."
    ),
    Intent.COMPENSATION: (
        "Thanks for your question about compensation. "
        "I'll check what details I can share for this role and follow up with you."
    ),
    Intent.OFFER: (
        "Thanks for your message about the offer. "
        "I'll review your question with the hiring team and get back to you."
    ),
    # Neutral on purpose: "Should I withdraw?" must not read as a confirmed withdrawal.
    Intent.WITHDRAWAL: (
        "Thank you for your message about withdrawing. "
        "I'll pass it on to the team and get back to you to confirm next steps."
    ),
    Intent.NETWORKING: (
        "Thanks for reaching out and for your interest in connecting. "
        "I'll be in touch if there's a suitable opportunity to talk."
    ),
    Intent.OTHER_OR_UNCLEAR: (
        "Thanks for your message. Could you share a little more detail about what you need "
        "so I can help?"
    ),
}

# Names come from untrusted input, so only plain names are echoed into a draft.
_LETTER = "A-Za-zÀ-ÖØ-öø-ÿ"  # Latin-1 letters, excluding × and ÷
_SAFE_NAME = re.compile(rf"^[{_LETTER}][{_LETTER} .'\-]{{0,59}}$")


def _greeting(candidate: str | None) -> str:
    if candidate and _SAFE_NAME.match(candidate):
        return f"Hi {candidate.split()[0]},"
    return "Hello,"


def score(text: str) -> dict[Intent, list[str]]:
    """Return the matched phrases per intent, for intents with any hits.

    Overlapping matches (e.g. "pay" inside "pay range") count as one phrase.
    """
    hits: dict[Intent, list[str]] = {}
    for intent, patterns in _COMPILED.items():
        spans = sorted(m.span() for p in patterns for m in p.finditer(text))
        merged: list[list[int]] = []
        for start, end in spans:
            if merged and start < merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        if merged:
            hits[intent] = [text[start:end] for start, end in merged]
    return hits


class MockProvider(AIProvider):
    name = "mock"

    def analyze(self, message: CandidateMessage) -> str:
        hits = score(message.text)
        warnings: list[str] = []
        ranked = sorted(hits.items(), key=lambda item: len(item[1]), reverse=True)

        if not ranked:
            intent, confidence = Intent.OTHER_OR_UNCLEAR, "low"
            reason = "No keyword rule matched."
        elif len(ranked) > 1 and len(ranked[0][1]) == len(ranked[1][1]):
            tied = [i.value for i, m in ranked if len(m) == len(ranked[0][1])]
            intent, confidence = Intent.OTHER_OR_UNCLEAR, "low"
            reason = f"Tied keyword matches between: {', '.join(tied)}."
        else:
            intent, matched = ranked[0]
            confidence = "high" if len(matched) >= 2 and len(ranked) == 1 else "medium"
            reason = f"Matched {len(matched)} keyword rule(s) for {intent.value}"
            if len(ranked) > 1:
                reason += f"; also matched {', '.join(i.value for i, _ in ranked[1:])}"
            reason += "."

        body = DRAFTS[intent]
        if intent == Intent.APPLICATION_STATUS:
            if message.application_status:
                body = (
                    "Thank you for checking in. Our records show your application status as: "
                    f"{message.application_status}. I'll let you know if anything changes."
                )
            else:
                warnings.append("Application status was not provided, so the draft does not state one.")

        return json.dumps({
            "message_id": message.message_id,
            "intent": intent.value,
            "confidence": confidence,
            "reason": reason,
            "draft_reply": f"{_greeting(message.candidate)}\n\n{body}",
            "needs_human_attention": confidence != "high" or bool(warnings),
            "warnings": warnings,
        })
