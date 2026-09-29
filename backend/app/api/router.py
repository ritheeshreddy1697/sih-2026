from fastapi import APIRouter

from app.api.routes.analytics import router as analytics_router
from app.api.routes.assistant import router as assistant_router
from app.api.routes.attendance import router as attendance_router
from app.api.routes.auth import router as auth_router
from app.api.routes.career import router as career_router
from app.api.routes.certificates import router as certificates_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.employment import router as employment_router
from app.api.routes.health import router as health_router
from app.api.routes.learning import router as learning_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.operations import router as operations_router
from app.api.routes.profiles import router as profiles_router
from app.api.routes.programmes import router as programmes_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(assistant_router, prefix="/assistant", tags=["platform assistant"])
api_router.include_router(attendance_router, prefix="/attendance", tags=["attendance"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
api_router.include_router(certificates_router, prefix="/certificates", tags=["certificates"])
api_router.include_router(career_router, prefix="/career", tags=["career counselling"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(employment_router, prefix="/employment", tags=["employment"])
api_router.include_router(programmes_router, prefix="/programmes", tags=["programmes"])
api_router.include_router(profiles_router, prefix="/profiles", tags=["profiles"])
api_router.include_router(learning_router, prefix="/learning", tags=["learning"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
api_router.include_router(operations_router, prefix="/operations", tags=["operations"])
