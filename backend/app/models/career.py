from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import (
    CareerConversationStatus,
    CareerEscalationStatus,
    CareerFeedbackRating,
    CareerLanguage,
    CareerMessageRole,
)

if TYPE_CHECKING:
    from app.models.auth import User


class CareerFaq(Base, TimestampMixin):
    __tablename__ = "career_faqs"
    __table_args__ = (UniqueConstraint("slug", "language", name="uq_career_faq_language"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(120), index=True)
    language: Mapped[CareerLanguage] = mapped_column(
        Enum(CareerLanguage, name="career_language", native_enum=False, length=8), index=True
    )
    category: Mapped[str] = mapped_column(String(80), index=True)
    question: Mapped[str] = mapped_column(String(500))
    answer: Mapped[str] = mapped_column(Text())
    keywords: Mapped[list[str]] = mapped_column(JSON(), default=list)
    platform_url: Mapped[str | None] = mapped_column(String(500))
    is_approved: Mapped[bool] = mapped_column(Boolean(), default=True, server_default="true")
    approved_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    approved_by: Mapped[User | None] = relationship()


class CareerConversation(Base, TimestampMixin):
    __tablename__ = "career_conversations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    language: Mapped[CareerLanguage] = mapped_column(
        Enum(CareerLanguage, name="career_conversation_language", native_enum=False, length=8),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(160), default="New conversation")
    status: Mapped[CareerConversationStatus] = mapped_column(
        Enum(
            CareerConversationStatus,
            name="career_conversation_status",
            native_enum=False,
            length=16,
        ),
        default=CareerConversationStatus.ACTIVE,
        server_default=CareerConversationStatus.ACTIVE.value,
        index=True,
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    user: Mapped[User] = relationship()
    messages: Mapped[list[CareerMessage]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    escalation: Mapped[CareerSupportEscalation | None] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", uselist=False
    )


class CareerMessage(Base):
    __tablename__ = "career_messages"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("career_conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[CareerMessageRole] = mapped_column(
        Enum(CareerMessageRole, name="career_message_role", native_enum=False, length=16),
        index=True,
    )
    content: Mapped[str] = mapped_column(Text())
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSON(), default=list)
    provider: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    conversation: Mapped[CareerConversation] = relationship(back_populates="messages")
    feedback: Mapped[CareerMessageFeedback | None] = relationship(
        back_populates="message", cascade="all, delete-orphan", uselist=False
    )


class CareerMessageFeedback(Base, TimestampMixin):
    __tablename__ = "career_message_feedback"
    __table_args__ = (UniqueConstraint("message_id", "user_id", name="uq_career_message_feedback"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    message_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("career_messages.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    rating: Mapped[CareerFeedbackRating] = mapped_column(
        Enum(
            CareerFeedbackRating,
            name="career_feedback_rating",
            native_enum=False,
            length=24,
        ),
        index=True,
    )
    comment: Mapped[str | None] = mapped_column(String(1000))

    message: Mapped[CareerMessage] = relationship(back_populates="feedback")
    user: Mapped[User] = relationship()


class CareerSupportEscalation(Base, TimestampMixin):
    __tablename__ = "career_support_escalations"
    __table_args__ = (UniqueConstraint("conversation_id", name="uq_career_support_conversation"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("career_conversations.id", ondelete="CASCADE"), index=True
    )
    requested_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    resolved_by_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    reason: Mapped[str] = mapped_column(String(2000))
    status: Mapped[CareerEscalationStatus] = mapped_column(
        Enum(
            CareerEscalationStatus,
            name="career_escalation_status",
            native_enum=False,
            length=16,
        ),
        default=CareerEscalationStatus.OPEN,
        server_default=CareerEscalationStatus.OPEN.value,
        index=True,
    )
    resolution_notes: Mapped[str | None] = mapped_column(String(2000))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    conversation: Mapped[CareerConversation] = relationship(back_populates="escalation")
    requested_by: Mapped[User] = relationship(foreign_keys=[requested_by_id])
    resolved_by: Mapped[User | None] = relationship(foreign_keys=[resolved_by_id])
