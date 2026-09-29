from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import AuthContext, get_current_auth
from app.core.config import settings
from app.db.session import get_db
from app.models import AuditLog
from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse
from app.services.auth import get_client_details
from app.services.platform_ai import (
    AssistantTurn,
    LocalPlatformGuide,
    PlatformAIError,
    PlatformAIProvider,
    PlatformAIRequest,
    get_platform_ai_provider,
)

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


def _enforce_rate_limit(db: Session, auth: AuthContext) -> None:
    since = datetime.now(UTC) - timedelta(minutes=1)
    count = db.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.user_id == auth.user.id,
            AuditLog.event_type == "assistant.message",
            AuditLog.created_at >= since,
        )
    )
    if int(count or 0) >= settings.career_chat_rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Assistant message limit reached. Please try again shortly.",
            headers={"Retry-After": "60"},
        )


@router.post("/chat", response_model=AssistantChatResponse)
def chat(
    payload: AssistantChatRequest,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(get_current_auth)],
    provider: Annotated[PlatformAIProvider, Depends(get_platform_ai_provider)],
) -> AssistantChatResponse:
    _enforce_rate_limit(db, auth)
    ai_request = PlatformAIRequest(
        language=payload.language,
        message=payload.message,
        history=[AssistantTurn(role=item.role, content=item.content) for item in payload.history],
        page_path=payload.page_path,
        role_names=[role.display_name for role in auth.user.roles],
    )
    used_local_fallback = False
    try:
        answer = provider.generate(ai_request)
        provider_name = provider.name
    except PlatformAIError:
        fallback = LocalPlatformGuide()
        answer = fallback.generate(ai_request)
        provider_name = fallback.name
        used_local_fallback = True

    ip_address, user_agent = get_client_details(request)
    db.add(
        AuditLog(
            user_id=auth.user.id,
            event_type="assistant.message",
            success=True,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"provider": provider_name, "page_path": payload.page_path},
        )
    )
    db.commit()
    return AssistantChatResponse(
        answer=answer,
        provider=provider_name,
        used_local_fallback=used_local_fallback,
    )
