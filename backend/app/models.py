"""Data shapes shared across the backend.

Candidate message text is untrusted data. These models only describe its shape;
nothing here interprets it as instructions.
"""

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Intent(str, Enum):
    APPLICATION_STATUS = "application_status"
    INTERVIEW_SCHEDULING = "interview_scheduling"
    INTERVIEW_FOLLOW_UP = "interview_follow_up"
    ROLE_INQUIRY = "role_inquiry"
    APPLICATION_SUBMISSION = "application_submission"
    COMPENSATION = "compensation"
    OFFER = "offer"
    WITHDRAWAL = "withdrawal"
    NETWORKING = "networking"
    OTHER_OR_UNCLEAR = "other_or_unclear"


INTENT_LABELS: dict[Intent, str] = {
    Intent.APPLICATION_STATUS: "Application status inquiry",
    Intent.INTERVIEW_SCHEDULING: "Interview scheduling / rescheduling",
    Intent.INTERVIEW_FOLLOW_UP: "Interview follow-up",
    Intent.ROLE_INQUIRY: "Job or role inquiry",
    Intent.APPLICATION_SUBMISSION: "Application submission / confirmation",
    Intent.COMPENSATION: "Salary or compensation inquiry",
    Intent.OFFER: "Offer-related inquiry",
    Intent.WITHDRAWAL: "Withdrawal or cancellation",
    Intent.NETWORKING: "Recruiter contact / networking",
    Intent.OTHER_OR_UNCLEAR: "Other or unclear",
}

# Confidence is a coarse band, not a probability. See Final directive.md for how
# each provider assigns it; the mock provider uses keyword-match counts.
Confidence = Literal["high", "medium", "low"]

MAX_MESSAGE_CHARS = 5000


class CandidateMessage(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message_id: str = Field(min_length=1, max_length=100)
    candidate: Optional[str] = Field(default=None, max_length=200)
    text: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    received_at: Optional[str] = None
    # Only ever set from recruiter-supplied input; never inferred.
    application_status: Optional[str] = Field(default=None, max_length=200)
    context: Optional[str] = Field(default=None, max_length=MAX_MESSAGE_CHARS)

    @field_validator("candidate", "received_at", "application_status", "context")
    @classmethod
    def blank_to_none(cls, value: Optional[str]) -> Optional[str]:
        return value or None


class MessageResult(BaseModel):
    message_id: str
    intent: Intent
    confidence: Confidence
    reason: str
    # None means no safe draft could be produced; `warnings` says why.
    draft_reply: Optional[str]
    needs_human_attention: bool
    warnings: list[str] = Field(default_factory=list)
    provider: str


MAX_BATCH = 200


class BatchRequest(BaseModel):
    # Rows are validated one at a time in app.batch, so one bad row can't reject the batch.
    messages: list[Any] = Field(min_length=1, max_length=MAX_BATCH)


class BatchMessageResult(MessageResult):
    row: int  # 1-based position in the submitted batch


class RowError(BaseModel):
    row: int
    message_id: Optional[str]
    errors: list[str]


class BatchSummary(BaseModel):
    received: int
    processed: int
    rejected: int


class IntentGroup(BaseModel):
    intent: Intent
    label: str
    count: int
    needs_attention_count: int
    # Ids, not copies: each result lives once in `results` and is referenced here.
    message_ids: list[str]


class BatchResponse(BaseModel):
    results: list[BatchMessageResult]
    groups: list[IntentGroup]
    errors: list[RowError]
    summary: BatchSummary
