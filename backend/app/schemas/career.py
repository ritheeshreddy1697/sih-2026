from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import (
    CareerConversationStatus,
    CareerEscalationStatus,
    CareerFeedbackRating,
    CareerLanguage,
    CareerMessageRole,
)


class CareerSourcePublic(BaseModel):
    source_type: Literal["faq", "programme", "job"]
    record_id: str
    title: str
    url: str
    summary: str


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: CareerLanguage = CareerLanguage.ENGLISH


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=2, max_length=2000)

    @field_validator("content")
    @classmethod
    def clean_content(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Message must contain at least two characters")
        return cleaned


class FeedbackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: CareerFeedbackRating
    comment: str | None = Field(default=None, max_length=1000)


class EscalationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=5, max_length=2000)


class EscalationResolve(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution_notes: str = Field(min_length=5, max_length=2000)


class MessageFeedbackPublic(BaseModel):
    id: UUID
    rating: CareerFeedbackRating
    comment: str | None


class CareerMessagePublic(BaseModel):
    id: UUID
    role: CareerMessageRole
    content: str
    sources: list[CareerSourcePublic]
    provider: str | None
    created_at: datetime
    feedback: MessageFeedbackPublic | None = None


class ConversationSummaryPublic(BaseModel):
    id: UUID
    language: CareerLanguage
    title: str
    status: CareerConversationStatus
    last_message_at: datetime
    created_at: datetime


class EscalationPublic(BaseModel):
    id: UUID
    conversation_id: UUID
    requested_by_id: UUID
    requester_name: str
    requester_email: str
    reason: str
    status: CareerEscalationStatus
    resolution_notes: str | None
    resolved_at: datetime | None
    created_at: datetime


class ConversationDetailPublic(ConversationSummaryPublic):
    messages: list[CareerMessagePublic]
    escalation: EscalationPublic | None


class MessageExchangePublic(BaseModel):
    user_message: CareerMessagePublic
    assistant_message: CareerMessagePublic
    used_local_fallback: bool
