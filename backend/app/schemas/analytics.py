from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

AnalyticsMetricKey = Literal[
    "registrations",
    "approved_participants",
    "attendance_percentage",
    "course_completion_rate",
    "assessment_improvement",
    "dropout_rate",
    "certificates_issued",
    "job_applications",
    "interviews",
    "placements",
]
AnalyticsUnit = Literal["count", "percent", "percentage_points"]
AnalyticsExportView = Literal["institution", "programme", "geography"]


class AnalyticsInstitutionOption(BaseModel):
    id: UUID
    name: str
    code: str
    state: str | None
    is_demo: bool


class AnalyticsProgrammeOption(BaseModel):
    id: UUID
    institution_id: UUID
    title: str
    code: str
    start_date: date
    is_demo: bool


class AnalyticsFilterOptions(BaseModel):
    institutions: list[AnalyticsInstitutionOption]
    programmes: list[AnalyticsProgrammeOption]
    states: list[str]
    genders: list[str]
    participant_categories: list[str]
    start_date_min: date | None
    start_date_max: date | None


class AnalyticsAppliedFilters(BaseModel):
    institution_id: UUID | None
    programme_id: UUID | None
    start_date: date | None
    end_date: date | None
    state: str | None
    gender: str | None
    participant_category: str | None


class AnalyticsMetric(BaseModel):
    key: AnalyticsMetricKey
    label: str
    value: float
    unit: AnalyticsUnit
    numerator: float
    denominator: float | None
    definition: str


class AnalyticsPerformanceRow(BaseModel):
    id: UUID
    label: str
    secondary_label: str
    is_demo: bool
    registrations: int
    approved_participants: int
    enrollments: int
    attendance_percentage: float
    course_completion_rate: float
    assessment_improvement: float
    dropout_rate: float
    certificates_issued: int
    job_applications: int
    interviews: int
    placements: int


class AnalyticsGeographyRow(BaseModel):
    state: str
    registrations: int = 0
    approved_participants: int = 0
    enrollments: int = 0
    certificates_issued: int = 0
    placements: int = 0


class AnalyticsDashboardResponse(BaseModel):
    generated_at: datetime
    scope_label: str
    contains_demo_data: bool
    filters: AnalyticsAppliedFilters
    metrics: list[AnalyticsMetric]
    institution_performance: list[AnalyticsPerformanceRow]
    programme_performance: list[AnalyticsPerformanceRow]
    geographic_distribution: list[AnalyticsGeographyRow]


class AnalyticsDrilldownColumn(BaseModel):
    key: str
    label: str


class AnalyticsDrilldownResponse(BaseModel):
    metric: AnalyticsMetricKey
    title: str
    definition: str
    columns: list[AnalyticsDrilldownColumn]
    rows: list[dict[str, str | int | float | None]]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    pages: int
