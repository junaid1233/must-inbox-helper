"""Provider-independent checks that add warnings for the human reviewer.

Both are heuristics and can miss cases; they exist so that obvious problems are
surfaced, not to guarantee detection. Neither changes the draft.
"""

import re

from app.validation import normalize_for_matching

# --- language ----------------------------------------------------------------

# Common function words that are not also common English words.
_FOREIGN_WORDS = {
    # Spanish
    "hola", "gracias", "hay", "alguna", "novedad", "novedades", "sobre", "solicitud", "mi", "el",
    "los", "las", "una", "por", "para", "estoy", "quiero", "saber", "puedo", "tengo", "entrevista",
    # French
    "bonjour", "merci", "je", "voudrais", "savoir", "où", "est", "ma", "candidature", "avec",
    "nous", "vous", "suis", "pas", "une", "les", "des", "du", "le",
    # German
    "hallo", "danke", "gibt", "es", "schon", "eine", "zu", "meiner", "meine", "bewerbung", "ich",
    "und", "nicht", "bitte", "ist",
    # Portuguese / Italian
    "olá", "obrigado", "obrigada", "gostaria", "há", "novidades", "minha", "não", "ciao", "grazie",
    "vorrei", "sapere", "della",
}
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def looks_non_english(text: str) -> bool:
    """True if the text is probably not English, or mixes in another language."""
    text = normalize_for_matching(text)
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    non_latin = sum(1 for c in letters if not ("a" <= c.lower() <= "z" or "À" <= c <= "ɏ"))
    if non_latin / len(letters) > 0.3:
        return True
    if "¿" in text or "¡" in text:
        return True
    words = [w.lower() for w in _WORD.findall(text)]
    foreign = sum(1 for w in words if w in _FOREIGN_WORDS)
    return foreign >= 3 or (foreign >= 2 and foreign / max(len(words), 1) > 0.25)


# --- conflicts ---------------------------------------------------------------

_WEEKDAYS = r"monday|tuesday|wednesday|thursday|friday|saturday|sunday"
_MONTHS = r"january|february|march|april|may|june|july|august|september|october|november|december"
_TIME_REF = re.compile(
    rf"\b(today|tomorrow|tonight|{_WEEKDAYS}|{_MONTHS}|\d{{1,2}}(:\d{{2}})?\s?(am|pm)|\d{{1,2}}:\d{{2}})\b",
    re.IGNORECASE,
)
_QUESTION_START = re.compile(r"^\s*(have|has|was|were|did|do|does|am|is|are|will|could|can)\b", re.I)


def _time_refs(text: str) -> set[str]:
    return {m.group(0).lower().replace(" ", "") for m in _TIME_REF.finditer(text)}


# Outcomes a candidate states about *themselves*. The draft-side outcome list is the
# wrong tool here: it flags "Congrats on your new role!" said to the recruiter.
_OUTCOME_WORDS = r"passed|selected|shortlisted|short-listed|hired|offered|successful|rejected|through"
_SELF_CLAIM = re.compile(
    r"\b(?:i(?:'ve|'d|'m| have| had| was| am)?\s+(?:been\s+|being\s+)?(?:" + _OUTCOME_WORDS + r")"
    r"|i\s+got\s+the\s+(?:job|offer|role)"
    r"|you\s+(?:offered|hired|selected|shortlisted)\s+me)\b",
    re.IGNORECASE,
)
# "tell me I've been hired" demands a claim rather than making one (injection handles that).
_DEMAND_BEFORE = re.compile(r"\b(?:tell|say|confirm|write|reply)\w*\s+(?:me\s+|to\s+me\s+)?(?:that\s+)?$", re.I)


def _claimed_outcome(text: str) -> str | None:
    """An outcome the candidate states (not asks about, not demands) about themselves."""
    for sentence in re.split(r"(?<=[.!?])\s+", normalize_for_matching(text)):
        if sentence.rstrip().endswith("?") and _QUESTION_START.search(sentence):
            continue  # "Have I passed?" asks, it doesn't claim
        for match in _SELF_CLAIM.finditer(sentence):
            if not _DEMAND_BEFORE.search(sentence[: match.start()]):
                return match.group(0)
    return None


def find_conflicts(text: str, context: str | None, application_status: str | None) -> list[str]:
    conflicts: list[str] = []

    claim = _claimed_outcome(text)
    if claim:
        if application_status:
            if claim.lower().split()[-1] not in application_status.lower():
                conflicts.append(f"Candidate says {claim!r}, but the recorded status is "
                                 f"{application_status!r}. Possible conflict; don't confirm either without checking.")
        else:
            conflicts.append(f"Candidate says {claim!r}, which is not in the supplied data. "
                             "Don't confirm it without checking.")

    if context:
        said, recorded = _time_refs(text), _time_refs(context)
        if said and recorded and not said & recorded:
            conflicts.append(f"Message mentions {', '.join(sorted(said))} but the context says "
                             f"{', '.join(sorted(recorded))}. Possible conflict; check before replying.")
    return conflicts
