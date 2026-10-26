"""Detect candidate text that tries to instruct the system (prompt injection).

Detection only flags the message for a human; it never changes what the provider
is told to do. Message text is always passed to providers as data. Like the
outcome check, this is a pattern list and cannot catch every phrasing.
"""

import re

from app.validation import normalize_for_matching

_OUTCOME_WORDS = r"(hired|selected|shortlisted|approved|passed|accepted|successful)"

INJECTION_PATTERNS = [
    r"(ignore|disregard|forget|override|overlook|pay\s+no\s+attention\s+to)\s+"
    r"(all\s+|any\s+|your\s+|the\s+|of\s+)*(previous\s+|prior\s+|above\s+|earlier\s+|preceding\s+|system\s+)?"
    r"(instructions|rules|prompts?|guidelines|directions|directives)",
    r"forget\s+everything",
    r"(system|developer)\s+prompt",
    r"developer\s+mode",
    r"you\s+are\s+now\s+(in\s+\w+\s+mode|an?\s+(ai|assistant|bot|model)|the\s+(hiring|recruit)\w*)",
    r"\bact\s+as\s+(the|an?)\s+(hiring|recruit|admin|system|assistant|ai)\w*",
    r"</?\s*(system|assistant|instructions?|message)\s*>",
    r"^\s*(system|assistant)\s*:",
    r"(reply|respond|answer)\s+only\s+with",
    r"new\s+(rule|instruction)s?\s*:",
    r"approve\s+(this|the|my)\s+(draft|reply|message)",
    r"send\s+(this|the)\s+(reply|message|email)\s+to\s+(all|every)",
    rf"mark\s+(me|every\s+\w+|all\s+\w+)\s+as\s+{_OUTCOME_WORDS}",
]
_INJECTION_RE = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in INJECTION_PATTERNS]


def find_injection_signals(text: str | None) -> list[str]:
    """Return the matched snippets, empty if none."""
    if not text:
        return []
    normalized = normalize_for_matching(text)
    return [m.group(0) for pattern in _INJECTION_RE if (m := pattern.search(normalized))]
