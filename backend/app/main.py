"""HTTP API. Classifies and drafts only; there is no endpoint that sends anything."""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.batch import process_batch
from app.config import get_settings
from app.csv_import import CsvFileError, parse_csv
from app.models import INTENT_LABELS, BatchRequest, BatchResponse, CandidateMessage, MessageResult
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


@app.post("/api/process-batch", response_model=BatchResponse)
def process_many(request: BatchRequest) -> BatchResponse:
    return process_batch(request.messages, provider)


class CsvImportRequest(BaseModel):
    csv: str = Field(min_length=1, max_length=1_000_000)


@app.post("/api/process-csv", response_model=BatchResponse)
def process_csv(request: CsvImportRequest) -> BatchResponse:
    try:
        records, problems = parse_csv(request.csv)
    except CsvFileError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return process_batch(records, provider, row_problems=problems)


SAMPLE_FILE = Path(__file__).resolve().parents[2] / "sample_data" / "messages.json"


@app.get("/api/sample")
def sample() -> dict:
    """The synthetic demo dataset, in the same shape /api/process-batch accepts."""
    data = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
    return {"messages": data["messages"]}
