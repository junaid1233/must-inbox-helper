from app.providers.base import AIProvider
from app.providers.mock import MockProvider


def build_provider(name: str) -> AIProvider:
    """Fail loudly on an unknown provider rather than silently falling back to mock."""
    if name == "mock":
        return MockProvider()
    raise ValueError(f"AI_PROVIDER={name!r} is not supported yet. Supported: 'mock'.")
