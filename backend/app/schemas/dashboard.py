from typing import Literal

from pydantic import BaseModel

from app.core.permissions import Permission
from app.models.enums import RoleCode

MetricTone = Literal["neutral", "success", "warning", "accent"]
ScheduleStatus = Literal["scheduled", "due", "completed", "pending", "confirmed"]


class DashboardMetric(BaseModel):
    label: str
    value: str
    change: str
    tone: MetricTone = "neutral"


class DashboardQuickAction(BaseModel):
    label: str
    description: str
    href: str
    permission: Permission


class DashboardScheduleItem(BaseModel):
    date_label: str
    title: str
    meta: str
    status: ScheduleStatus


class DashboardActivityItem(BaseModel):
    title: str
    description: str
    time_label: str


class DashboardNotification(BaseModel):
    id: str
    title: str
    description: str
    unread: bool = True


class DashboardResponse(BaseModel):
    dashboard_key: RoleCode
    title: str
    description: str
    metrics: list[DashboardMetric]
    quick_actions: list[DashboardQuickAction]
    schedule_title: str
    schedule: list[DashboardScheduleItem]
    activity: list[DashboardActivityItem]
    notifications: list[DashboardNotification]
