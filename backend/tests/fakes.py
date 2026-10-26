"""Test doubles for provider behaviour that the mock provider never produces."""

from app.models import CandidateMessage
from app.providers.base import AIProvider


class StaticProvider(AIProvider):
    """Returns a fixed raw string, e.g. malformed model output."""

    name = "static"

    def __init__(self, raw: str):
        self.raw = raw

    def analyze(self, message: CandidateMessage) -> str:
        return self.raw


class RaisingProvider(AIProvider):
    name = "raising"

    def __init__(self, exc: Exception):
        self.exc = exc

    def analyze(self, message: CandidateMessage) -> str:
        raise self.exc
