from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

NotificationTargetType = Literal["trainees", "trainers", "institutions"]


class NotificationSendRequest(BaseModel):
    target_type: NotificationTargetType
    target_ids: list[UUID] = Field(min_length=1, max_length=100)
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=3, max_length=1000)


class NotificationSendResponse(BaseModel):
    id: UUID
    sent_count: int


class NotificationPublic(BaseModel):
    id: UUID
    title: str
    description: str
    sender_name: str
    created_at: datetime
    unread: bool


class NotificationListResponse(BaseModel):
    items: list[NotificationPublic]
    unread_count: int
