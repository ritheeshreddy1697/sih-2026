from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import AuthContext, require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.enums import CareerEscalationStatus
from app.schemas.career import (
    ConversationCreate,
    ConversationDetailPublic,
    ConversationSummaryPublic,
    EscalationCreate,
    EscalationPublic,
    EscalationResolve,
    FeedbackCreate,
    MessageCreate,
    MessageExchangePublic,
    MessageFeedbackPublic,
)
from app.services import career as career_service
from app.services.career_ai import CareerAIProvider, get_career_ai_provider

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/conversations", response_model=list[ConversationSummaryPublic])
def get_conversations(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.CAREER_COUNSELLING))],
) -> list[ConversationSummaryPublic]:
    return career_service.list_conversations(db, auth.user)


@router.post(
    "/conversations",
    response_model=ConversationDetailPublic,
    status_code=status.HTTP_201_CREATED,
)
def start_conversation(
    payload: ConversationCreate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.CAREER_COUNSELLING))],
) -> ConversationDetailPublic:
    return career_service.create_conversation(db, request, auth.user, payload.language)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailPublic)
def get_conversation(
    conversation_id: UUID,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.CAREER_COUNSELLING))],
) -> ConversationDetailPublic:
    return career_service.get_conversation(db, auth.user, conversation_id)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageExchangePublic,
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    conversation_id: UUID,
    payload: MessageCreate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.CAREER_COUNSELLING))],
    provider: Annotated[CareerAIProvider, Depends(get_career_ai_provider)],
) -> MessageExchangePublic:
    return career_service.send_message(
        db,
        request,
        auth.user,
        conversation_id,
        payload.content,
        provider,
    )


@router.put(
    "/conversations/{conversation_id}/messages/{message_id}/feedback",
    response_model=MessageFeedbackPublic,
)
def record_feedback(
    conversation_id: UUID,
    message_id: UUID,
    payload: FeedbackCreate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.CAREER_COUNSELLING))],
) -> MessageFeedbackPublic:
    return career_service.save_feedback(
        db,
        request,
        auth.user,
        conversation_id,
        message_id,
        payload,
    )


@router.post(
    "/conversations/{conversation_id}/escalate",
    response_model=EscalationPublic,
    status_code=status.HTTP_201_CREATED,
)
def escalate_conversation(
    conversation_id: UUID,
    payload: EscalationCreate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.CAREER_COUNSELLING))],
) -> EscalationPublic:
    return career_service.request_support(
        db,
        request,
        auth.user,
        conversation_id,
        payload.reason,
    )


@router.get("/support", response_model=list[EscalationPublic])
def get_support_requests(
    db: DbSession,
    _: Annotated[AuthContext, Depends(require_permission(Permission.CAREER_SUPPORT))],
    escalation_status: CareerEscalationStatus | None = None,
) -> list[EscalationPublic]:
    return career_service.list_support_requests(db, escalation_status)


@router.patch("/support/{escalation_id}", response_model=EscalationPublic)
def resolve_support_request(
    escalation_id: UUID,
    payload: EscalationResolve,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.CAREER_SUPPORT))],
) -> EscalationPublic:
    return career_service.resolve_support_request(
        db,
        request,
        auth.user,
        escalation_id,
        payload.resolution_notes,
    )
