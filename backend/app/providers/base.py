"""Provider interface.

A provider turns one candidate message into *raw* output: a JSON string with
`message_id`, `intent`, `confidence`, `reason` and `draft_reply`. Providers are
not trusted to return valid data; `app.validation` checks everything they return.
"""

from abc import ABC, abstractmethod

from app.models import CandidateMessage


class ProviderError(Exception):
    """The provider could not produce output at all."""


class ProviderTimeout(ProviderError):
    pass


class ProviderUnavailable(ProviderError):
    pass


class AIProvider(ABC):
    name: str

    @abstractmethod
    def analyze(self, message: CandidateMessage) -> str:
        """Return raw JSON text for one message. May raise ProviderError."""
