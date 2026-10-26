"""HTTP API. Classifies and drafts only; there is no endpoint that sends anything."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models import INTENT_LABELS, CandidateMessage, MessageResult
from app.pipeline import process_message
from app.providers import build_provider

settings = get_settings()
provider = build_provider(settings.ai_provider)

app = FastAPI(title="Inbox Helper", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "provider": provider.name,
        "demo_mode": provider.name == "mock",
        "sends_messages": False,
    }


@app.get("/api/intents")
def intents() -> dict[str, str]:
    return {intent.value: label for intent, label in INTENT_LABELS.items()}


@app.post("/api/process", response_model=MessageResult)
def process(message: CandidateMessage) -> MessageResult:
    return process_message(message, provider)
