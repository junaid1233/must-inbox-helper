"""Settings from environment variables (optionally a .env file in the repo root or backend/)."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent.parent
for env_file in (_BACKEND_DIR / ".env", _BACKEND_DIR.parent / ".env"):
    load_dotenv(env_file, override=False)


@dataclass(frozen=True)
class Settings:
    ai_provider: str
    frontend_origin: str


def get_settings() -> Settings:
    return Settings(
        ai_provider=os.getenv("AI_PROVIDER", "mock").strip().lower(),
        frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").strip(),
    )
