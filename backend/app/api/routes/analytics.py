from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.api.dependencies import AuthContext, require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models import AuditLog, EligibilityType
from app.schemas.analytics import (
    AnalyticsDashboardResponse,
    AnalyticsDrilldownResponse,
    AnalyticsExportView,
    AnalyticsFilterOptions,
    AnalyticsMetricKey,
)
from app.services import analytics as analytics_service
from app.services.auth import get_client_details

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
AnalyticsAuth = Annotated[
    AuthContext,
    Depends(require_permission(Permission.ANALYTICS_VIEW)),
]


def filters_from_query(
    institution_id: UUID | None,
    programme_id: UUID | None,
    start_date: date | None,
    end_date: date | None,
    state: str | None,
    gender: str | None,
    participant_category: EligibilityType | None,
) -> analytics_service.AnalyticsFilters:
    return analytics_service.AnalyticsFilters(
        institution_id=institution_id,
        programme_id=programme_id,
        start_date=start_date,
        end_date=end_date,
        state=state,
        gender=gender,
        participant_category=participant_category.value if participant_category else None,
    )


@router.get("/options", response_model=AnalyticsFilterOptions)
def analytics_options(db: DbSession, auth: AnalyticsAuth) -> AnalyticsFilterOptions:
    return analytics_service.filter_options(db, auth.user)


@router.get("/dashboard", response_model=AnalyticsDashboardResponse)
def analytics_dashboard(
    db: DbSession,
    auth: AnalyticsAuth,
    institution_id: UUID | None = None,
    programme_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    state: Annotated[str | None, Query(max_length=120)] = None,
    gender: Annotated[str | None, Query(max_length=80)] = None,
    participant_category: EligibilityType | None = None,
) -> AnalyticsDashboardResponse:
    return analytics_service.dashboard(
        db,
        auth.user,
        filters_from_query(
            institution_id,
            programme_id,
            start_date,
            end_date,
            state,
            gender,
            participant_category,
        ),
    )


@router.get("/drilldown/{metric}", response_model=AnalyticsDrilldownResponse)
def analytics_drilldown(
    metric: AnalyticsMetricKey,
    db: DbSession,
    auth: AnalyticsAuth,
    institution_id: UUID | None = None,
    programme_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    state: Annotated[str | None, Query(max_length=120)] = None,
    gender: Annotated[str | None, Query(max_length=80)] = None,
    participant_category: EligibilityType | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AnalyticsDrilldownResponse:
    return analytics_service.drilldown(
        db,
        auth.user,
        filters_from_query(
            institution_id,
            programme_id,
            start_date,
            end_date,
            state,
            gender,
            participant_category,
        ),
        metric,
        page,
        page_size,
    )


@router.get("/export")
def analytics_export(
    request: Request,
    db: DbSession,
    auth: AnalyticsAuth,
    view: AnalyticsExportView = "programme",
    institution_id: UUID | None = None,
    programme_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    state: Annotated[str | None, Query(max_length=120)] = None,
    gender: Annotated[str | None, Query(max_length=80)] = None,
    participant_category: EligibilityType | None = None,
) -> Response:
    filters = filters_from_query(
        institution_id,
        programme_id,
        start_date,
        end_date,
        state,
        gender,
        participant_category,
    )
    data = analytics_service.dashboard(db, auth.user, filters)
    ip_address, user_agent = get_client_details(request)
    db.add(
        AuditLog(
            user_id=auth.user.id,
            event_type="analytics.exported",
            success=True,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"view": view, "filters": data.filters.model_dump(mode="json")},
        )
    )
    db.commit()
    filename = f"ncct-analytics-{view}-{date.today().isoformat()}.csv"
    return Response(
        content=analytics_service.export_csv(data, view),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
