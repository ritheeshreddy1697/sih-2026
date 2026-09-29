from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import settings
from app.models import (
    AuditLog,
    CareerConversation,
    CareerConversationStatus,
    CareerEscalationStatus,
    CareerFaq,
    CareerLanguage,
    CareerMessage,
    CareerMessageFeedback,
    CareerMessageRole,
    CareerSupportEscalation,
    Programme,
    RoleCode,
    User,
)
from app.schemas.career import (
    CareerMessagePublic,
    CareerSourcePublic,
    ConversationDetailPublic,
    ConversationSummaryPublic,
    EscalationPublic,
    FeedbackCreate,
    MessageExchangePublic,
    MessageFeedbackPublic,
)
from app.services import employment as employment_service
from app.services import programmes as programme_service
from app.services.auth import get_client_details
from app.services.career_ai import (
    CareerAIError,
    CareerAIProvider,
    CareerAIRequest,
    GroundingSource,
    LocalFaqProvider,
    ProviderMessage,
)

INTENT_TERMS = {
    "programme": {
        "programme",
        "program",
        "course",
        "training",
        "eligibility",
        "apply",
        "कार्यक्रम",
        "प्रशिक्षण",
        "पाठ्यक्रम",
        "योग्यता",
        "కార్యక్రమం",
        "శిక్షణ",
        "కోర్సు",
        "అర్హత",
    },
    "job": {
        "job",
        "jobs",
        "employment",
        "vacancy",
        "role",
        "नौकरी",
        "रोज़गार",
        "रिक्ति",
        "ఉద్యోగం",
        "ఉద్యోగాలు",
        "ఖాళీ",
    },
    "resume": {"resume", "cv", "résumé", "रिज्यूमे", "बायोडाटा", "రెజ్యూమే", "సీవీ"},
    "interview": {"interview", "साक्षात्कार", "इंटरव्यू", "ఇంటర్వ్యూ"},
    "entrepreneurship": {
        "enterprise",
        "entrepreneur",
        "entrepreneurship",
        "business",
        "cooperative",
        "scheme",
        "उद्यम",
        "व्यवसाय",
        "सहकारी",
        "योजना",
        "వ్యాపారం",
        "సహకార",
        "ఎంటర్‌ప్రైజ్",
        "పథకం",
    },
    "navigation": {
        "where",
        "find",
        "page",
        "navigate",
        "platform",
        "कहाँ",
        "पेज",
        "ఎక్కడ",
        "పేజీ",
    },
}

UNAVAILABLE = {
    CareerLanguage.ENGLISH: (
        "I could not find approved platform information for that request. "
        "Try asking about available programmes, published jobs, resumes or interviews, "
        "or send this conversation to human support."
    ),
    CareerLanguage.HINDI: (
        "इस अनुरोध के लिए स्वीकृत प्लेटफ़ॉर्म जानकारी नहीं मिली। उपलब्ध कार्यक्रमों, "
        "प्रकाशित नौकरियों, रिज़्यूमे या साक्षात्कार के बारे में पूछें, या इस बातचीत को "
        "मानव सहायता टीम को भेजें।"
    ),
    CareerLanguage.TELUGU: (
        "ఈ అభ్యర్థనకు ఆమోదించబడిన ప్లాట్‌ఫారమ్ సమాచారం కనుగొనబడలేదు. అందుబాటులో ఉన్న "
        "శిక్షణలు, ప్రచురించిన ఉద్యోగాలు, రెజ్యూమే లేదా ఇంటర్వ్యూ గురించి అడగండి, లేదా ఈ "
        "సంభాషణను సహాయక బృందానికి పంపండి."
    ),
}


def utc_now() -> datetime:
    return datetime.now(UTC)


def display_name(user: User) -> str:
    return user.profile.full_name if user.profile else user.email


def add_audit(
    db: Session,
    request: Request,
    user: User,
    event_type: str,
    details: dict[str, Any],
) -> None:
    ip_address, user_agent = get_client_details(request)
    db.add(
        AuditLog(
            user_id=user.id,
            event_type=event_type,
            success=True,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )
    )


def ensure_trainee(user: User) -> None:
    if RoleCode.TRAINEE not in {role.code for role in user.roles}:
        raise HTTPException(status_code=403, detail="Career counselling is available to trainees")


def conversation_options() -> tuple[Any, ...]:
    return (
        selectinload(CareerConversation.messages).selectinload(CareerMessage.feedback),
        joinedload(CareerConversation.escalation).joinedload(CareerSupportEscalation.requested_by),
    )


def load_conversation(db: Session, user: User, conversation_id: UUID) -> CareerConversation:
    conversation = db.scalar(
        select(CareerConversation)
        .where(
            CareerConversation.id == conversation_id,
            CareerConversation.user_id == user.id,
        )
        .options(*conversation_options())
        .execution_options(populate_existing=True)
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


def source_public(source: dict[str, Any]) -> CareerSourcePublic:
    return CareerSourcePublic.model_validate(source)


def feedback_public(feedback: CareerMessageFeedback | None) -> MessageFeedbackPublic | None:
    if feedback is None:
        return None
    return MessageFeedbackPublic(
        id=feedback.id,
        rating=feedback.rating,
        comment=feedback.comment,
    )


def message_public(message: CareerMessage) -> CareerMessagePublic:
    return CareerMessagePublic(
        id=message.id,
        role=message.role,
        content=message.content,
        sources=[source_public(source) for source in message.sources],
        provider=message.provider,
        created_at=message.created_at,
        feedback=feedback_public(message.feedback),
    )


def escalation_public(escalation: CareerSupportEscalation) -> EscalationPublic:
    return EscalationPublic(
        id=escalation.id,
        conversation_id=escalation.conversation_id,
        requested_by_id=escalation.requested_by_id,
        requester_name=display_name(escalation.requested_by),
        requester_email=escalation.requested_by.email,
        reason=escalation.reason,
        status=escalation.status,
        resolution_notes=escalation.resolution_notes,
        resolved_at=escalation.resolved_at,
        created_at=escalation.created_at,
    )


def conversation_summary(conversation: CareerConversation) -> ConversationSummaryPublic:
    return ConversationSummaryPublic(
        id=conversation.id,
        language=conversation.language,
        title=conversation.title,
        status=conversation.status,
        last_message_at=conversation.last_message_at,
        created_at=conversation.created_at,
    )


def conversation_detail(conversation: CareerConversation) -> ConversationDetailPublic:
    return ConversationDetailPublic(
        **conversation_summary(conversation).model_dump(),
        messages=[
            message_public(message)
            for message in sorted(conversation.messages, key=lambda item: item.created_at)
        ],
        escalation=(
            escalation_public(conversation.escalation) if conversation.escalation else None
        ),
    )


def create_conversation(
    db: Session, request: Request, user: User, language: CareerLanguage
) -> ConversationDetailPublic:
    ensure_trainee(user)
    conversation = CareerConversation(user_id=user.id, language=language)
    db.add(conversation)
    db.flush()
    add_audit(
        db,
        request,
        user,
        "career.conversation_created",
        {"conversation_id": str(conversation.id), "language": language.value},
    )
    db.commit()
    return conversation_detail(load_conversation(db, user, conversation.id))


def list_conversations(db: Session, user: User) -> list[ConversationSummaryPublic]:
    ensure_trainee(user)
    conversations = db.scalars(
        select(CareerConversation)
        .where(CareerConversation.user_id == user.id)
        .order_by(CareerConversation.last_message_at.desc())
    )
    return [conversation_summary(item) for item in conversations]


def get_conversation(db: Session, user: User, conversation_id: UUID) -> ConversationDetailPublic:
    ensure_trainee(user)
    return conversation_detail(load_conversation(db, user, conversation_id))


def _tokens(value: str) -> set[str]:
    return {token.casefold() for token in re.findall(r"[^\W_]+", value, flags=re.UNICODE)}


def classify_intent(message: str) -> str:
    tokens = _tokens(message)
    ranked = sorted(
        ((len(tokens & terms), intent) for intent, terms in INTENT_TERMS.items()),
        reverse=True,
    )
    return ranked[0][1] if ranked and ranked[0][0] else "faq"


def _faq_sources(
    db: Session,
    language: CareerLanguage,
    message: str,
    intent: str,
    limit: int = 3,
) -> list[CareerSourcePublic]:
    faqs = list(
        db.scalars(
            select(CareerFaq)
            .where(
                CareerFaq.language == language,
                CareerFaq.is_approved.is_(True),
            )
            .order_by(CareerFaq.slug)
        )
    )
    message_tokens = _tokens(message)

    def score(faq: CareerFaq) -> int:
        faq_tokens = _tokens(f"{faq.question} {' '.join(faq.keywords)}")
        return len(message_tokens & faq_tokens) * 3 + (4 if faq.category == intent else 0)

    ranked = sorted(faqs, key=lambda item: (score(item), item.slug), reverse=True)
    selected = [item for item in ranked if score(item) > 0][:limit]
    return [
        CareerSourcePublic(
            source_type="faq",
            record_id=str(faq.id),
            title=faq.question,
            url=faq.platform_url or "/career-counsellor",
            summary=faq.answer,
        )
        for faq in selected
    ]


def _programme_sources(
    db: Session, user: User, message: str, limit: int = 4
) -> list[CareerSourcePublic]:
    available = [item for item in programme_service.list_programmes(db, user) if item.can_apply]
    message_tokens = _tokens(message)
    profile = user.trainee_profile
    preference_text = ""
    if profile is not None:
        preference_text = " ".join(
            [
                profile.preferred_language or "",
                profile.preferred_location or "",
                profile.career_interests or "",
                " ".join(profile.skills),
            ]
        )
    preference_tokens = _tokens(preference_text)

    def score(item: Any) -> int:
        haystack = _tokens(
            f"{item.title} {item.summary} {item.mode.value} {item.language} {item.location or ''}"
        )
        return len(message_tokens & haystack) * 4 + len(preference_tokens & haystack)

    ranked = sorted(available, key=lambda item: (score(item), item.start_date), reverse=True)
    if any(score(item) for item in ranked):
        ranked = [item for item in ranked if score(item) > 0]
    sources = []
    for item in ranked[:limit]:
        programme = db.scalar(select(Programme).where(Programme.id == item.id))
        if programme is None:
            continue
        location = programme.location or "Online"
        sources.append(
            CareerSourcePublic(
                source_type="programme",
                record_id=str(programme.id),
                title=f"{programme.title} ({programme.code})",
                url=f"/programmes/{programme.id}",
                summary=(
                    f"{programme.summary} Eligibility: {programme.eligibility_criteria} "
                    f"Mode: {programme.mode.value}. Language: {programme.language}. "
                    f"Location: {location}. Duration: {programme.duration_days} days. "
                    f"Application deadline: {programme.application_deadline.date().isoformat()}."
                ),
            )
        )
    return sources


def _job_sources(db: Session, user: User, message: str, limit: int = 4) -> list[CareerSourcePublic]:
    jobs = employment_service.recommendations(db, user)
    message_tokens = _tokens(message)

    def score(item: Any) -> int:
        haystack = _tokens(
            f"{item.title} {item.description} {item.company_name} {item.location} "
            f"{' '.join(item.required_skills + item.preferred_skills)}"
        )
        return len(message_tokens & haystack) * 4 + (item.match.score if item.match else 0)

    ranked = sorted(jobs, key=score, reverse=True)
    sources = []
    for job in ranked[:limit]:
        reasons = "; ".join(job.match.reasons) if job.match else "No matching explanation available"
        deadline = (
            job.application_deadline.date().isoformat() if job.application_deadline else "Open"
        )
        sources.append(
            CareerSourcePublic(
                source_type="job",
                record_id=str(job.id),
                title=f"{job.title} at {job.company_name}",
                url=f"/employment?job={job.id}",
                summary=(
                    f"Location: {job.location}. Mode: {job.workplace_mode.value}. "
                    f"Required verified skills: {', '.join(job.required_skills) or 'None listed'}. "
                    f"Application deadline: {deadline}. Match explanation: {reasons}."
                ),
            )
        )
    return sources


def retrieve_sources(
    db: Session,
    user: User,
    language: CareerLanguage,
    message: str,
    intent: str,
) -> list[CareerSourcePublic]:
    if intent == "programme":
        return _programme_sources(db, user, message)
    if intent == "job":
        return _job_sources(db, user, message)
    return _faq_sources(db, language, message, intent)


def _record_answer(language: CareerLanguage, intent: str, sources: list[CareerSourcePublic]) -> str:
    if not sources:
        return UNAVAILABLE[language]
    count = len(sources)
    headings = {
        CareerLanguage.ENGLISH: {
            "programme": f"I found {count} currently available programme(s) in the platform.",
            "job": f"I found {count} published job(s) from verified employers.",
        },
        CareerLanguage.HINDI: {
            "programme": f"प्लेटफ़ॉर्म पर {count} उपलब्ध कार्यक्रम मिले।",
            "job": f"सत्यापित नियोक्ताओं की {count} प्रकाशित नौकरियाँ मिलीं।",
        },
        CareerLanguage.TELUGU: {
            "programme": f"ప్లాట్‌ఫారమ్‌లో ప్రస్తుతం అందుబాటులో ఉన్న {count} శిక్షణలు కనిపించాయి.",
            "job": f"ధృవీకరించిన యజమానుల నుండి {count} ప్రచురించిన ఉద్యోగాలు కనిపించాయి.",
        },
    }
    lines = [headings[language][intent]]
    for index, source in enumerate(sources, 1):
        prefix = "P" if intent == "programme" else "J"
        lines.append(f"[{prefix}{index}] {source.title}: {source.summary}")
    return "\n\n".join(lines)


def _sanitize_provider_answer(answer: str, source_keys: set[str]) -> str:
    answer = re.sub(r"\[([^\]]+)]\((?:https?://|//)[^)]+\)", r"\1", answer)
    answer = re.sub(r"https?://\S+", "", answer)

    def clean_citation(match: re.Match[str]) -> str:
        return match.group(0) if match.group(1) in source_keys else ""

    answer = re.sub(r"\[([A-Z]\d+)]", clean_citation, answer)
    return answer.strip()[:5000]


def _provider_answer(
    provider: CareerAIProvider,
    language: CareerLanguage,
    intent: str,
    content: str,
    history: list[ProviderMessage],
    sources: list[CareerSourcePublic],
) -> tuple[str, str, bool]:
    grounded = [
        GroundingSource(
            key=f"F{index}",
            title=source.title,
            content=source.summary,
            url=source.url,
        )
        for index, source in enumerate(sources, 1)
    ]
    request = CareerAIRequest(
        language=language,
        intent=intent,
        message=content,
        history=history,
        sources=grounded,
    )
    used_fallback = isinstance(provider, LocalFaqProvider)
    active_provider = provider
    try:
        answer = provider.generate(request)
    except CareerAIError:
        active_provider = LocalFaqProvider()
        answer = active_provider.generate(request)
        used_fallback = True
    answer = _sanitize_provider_answer(answer, {source.key for source in grounded})
    if not answer:
        answer = UNAVAILABLE[language]
        used_fallback = True
    if grounded and not any(f"[{source.key}]" in answer for source in grounded):
        answer = f"{answer}\n\nSource: [{grounded[0].key}]"
    return answer, active_provider.name, used_fallback


def _check_rate_limit(db: Session, user: User) -> None:
    since = utc_now() - timedelta(minutes=1)
    recent_count = db.scalar(
        select(func.count(CareerMessage.id))
        .join(CareerConversation)
        .where(
            CareerConversation.user_id == user.id,
            CareerMessage.role == CareerMessageRole.USER,
            CareerMessage.created_at >= since,
        )
    )
    if int(recent_count or 0) >= settings.career_chat_rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Message limit reached. Please wait a minute and try again.",
            headers={"Retry-After": "60"},
        )


def send_message(
    db: Session,
    request: Request,
    user: User,
    conversation_id: UUID,
    content: str,
    provider: CareerAIProvider,
) -> MessageExchangePublic:
    ensure_trainee(user)
    if len(content) > settings.career_chat_max_input_chars:
        raise HTTPException(status_code=422, detail="Message is too long")
    conversation = load_conversation(db, user, conversation_id)
    if conversation.status == CareerConversationStatus.CLOSED:
        raise HTTPException(status_code=409, detail="This conversation is closed")
    _check_rate_limit(db, user)

    history = [
        ProviderMessage(role=item.role.value, content=item.content)
        for item in sorted(conversation.messages, key=lambda item: item.created_at)[-8:]
    ]
    intent = classify_intent(content)
    sources = retrieve_sources(db, user, conversation.language, content, intent)
    if intent in {"programme", "job"}:
        answer = _record_answer(conversation.language, intent, sources)
        provider_name = "platform-retrieval"
        used_fallback = False
    elif not sources:
        answer = UNAVAILABLE[conversation.language]
        provider_name = "local-faq"
        used_fallback = True
    elif intent in {"entrepreneurship", "navigation"}:
        answer, provider_name, used_fallback = _provider_answer(
            LocalFaqProvider(),
            conversation.language,
            intent,
            content,
            history,
            sources,
        )
    else:
        answer, provider_name, used_fallback = _provider_answer(
            provider,
            conversation.language,
            intent,
            content,
            history,
            sources,
        )

    source_payload = [source.model_dump(mode="json") for source in sources]
    message_time = utc_now()
    user_message = CareerMessage(
        conversation_id=conversation.id,
        role=CareerMessageRole.USER,
        content=content,
        sources=[],
        created_at=message_time,
    )
    assistant_message = CareerMessage(
        conversation_id=conversation.id,
        role=CareerMessageRole.ASSISTANT,
        content=answer,
        sources=source_payload,
        provider=provider_name,
        created_at=message_time + timedelta(microseconds=1),
    )
    db.add_all([user_message, assistant_message])
    conversation.last_message_at = assistant_message.created_at
    if conversation.title == "New conversation":
        conversation.title = content[:157] + ("..." if len(content) > 157 else "")
    db.flush()
    add_audit(
        db,
        request,
        user,
        "career.message_sent",
        {
            "conversation_id": str(conversation.id),
            "message_id": str(user_message.id),
            "intent": intent,
            "source_count": len(sources),
            "provider": provider_name,
            "used_local_fallback": used_fallback,
        },
    )
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)
    return MessageExchangePublic(
        user_message=message_public(user_message),
        assistant_message=message_public(assistant_message),
        used_local_fallback=used_fallback,
    )


def save_feedback(
    db: Session,
    request: Request,
    user: User,
    conversation_id: UUID,
    message_id: UUID,
    payload: FeedbackCreate,
) -> MessageFeedbackPublic:
    ensure_trainee(user)
    conversation = load_conversation(db, user, conversation_id)
    message = next((item for item in conversation.messages if item.id == message_id), None)
    if message is None or message.role != CareerMessageRole.ASSISTANT:
        raise HTTPException(status_code=404, detail="Assistant message not found")
    feedback = db.scalar(
        select(CareerMessageFeedback).where(
            CareerMessageFeedback.message_id == message.id,
            CareerMessageFeedback.user_id == user.id,
        )
    )
    if feedback is None:
        feedback = CareerMessageFeedback(message_id=message.id, user_id=user.id)
        db.add(feedback)
    feedback.rating = payload.rating
    feedback.comment = payload.comment
    add_audit(
        db,
        request,
        user,
        "career.feedback_recorded",
        {"message_id": str(message.id), "rating": payload.rating.value},
    )
    db.commit()
    db.refresh(feedback)
    result = feedback_public(feedback)
    if result is None:
        raise RuntimeError("Persisted feedback could not be serialized")
    return result


def request_support(
    db: Session,
    request: Request,
    user: User,
    conversation_id: UUID,
    reason: str,
) -> EscalationPublic:
    ensure_trainee(user)
    conversation = load_conversation(db, user, conversation_id)
    escalation = conversation.escalation
    if escalation is not None and escalation.status == CareerEscalationStatus.OPEN:
        return escalation_public(escalation)
    if escalation is None:
        escalation = CareerSupportEscalation(
            conversation_id=conversation.id,
            requested_by_id=user.id,
            reason=reason,
        )
        db.add(escalation)
    else:
        escalation.reason = reason
        escalation.status = CareerEscalationStatus.OPEN
        escalation.resolved_by_id = None
        escalation.resolution_notes = None
        escalation.resolved_at = None
    conversation.status = CareerConversationStatus.ESCALATED
    db.flush()
    add_audit(
        db,
        request,
        user,
        "career.support_requested",
        {"conversation_id": str(conversation.id), "escalation_id": str(escalation.id)},
    )
    db.commit()
    return escalation_public(
        db.scalar(
            select(CareerSupportEscalation)
            .where(CareerSupportEscalation.id == escalation.id)
            .options(joinedload(CareerSupportEscalation.requested_by))
        )
        or escalation
    )


def list_support_requests(
    db: Session, escalation_status: CareerEscalationStatus | None
) -> list[EscalationPublic]:
    statement = (
        select(CareerSupportEscalation)
        .options(joinedload(CareerSupportEscalation.requested_by))
        .order_by(CareerSupportEscalation.created_at.desc())
    )
    if escalation_status is not None:
        statement = statement.where(CareerSupportEscalation.status == escalation_status)
    return [escalation_public(item) for item in db.scalars(statement)]


def resolve_support_request(
    db: Session,
    request: Request,
    user: User,
    escalation_id: UUID,
    resolution_notes: str,
) -> EscalationPublic:
    escalation = db.scalar(
        select(CareerSupportEscalation)
        .where(CareerSupportEscalation.id == escalation_id)
        .options(
            joinedload(CareerSupportEscalation.requested_by),
            joinedload(CareerSupportEscalation.conversation),
        )
    )
    if escalation is None:
        raise HTTPException(status_code=404, detail="Support request not found")
    escalation.status = CareerEscalationStatus.RESOLVED
    escalation.resolved_by_id = user.id
    escalation.resolution_notes = resolution_notes
    escalation.resolved_at = utc_now()
    escalation.conversation.status = CareerConversationStatus.ACTIVE
    add_audit(
        db,
        request,
        user,
        "career.support_resolved",
        {"escalation_id": str(escalation.id)},
    )
    db.commit()
    db.refresh(escalation)
    return escalation_public(escalation)
