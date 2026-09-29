from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import AuthContext, get_current_auth
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard import get_dashboard

router = APIRouter()


@router.get("", response_model=DashboardResponse)
def dashboard(auth: Annotated[AuthContext, Depends(get_current_auth)]) -> DashboardResponse:
    try:
        return get_dashboard({role.code for role in auth.user.roles})
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No dashboard is available for this account",
        ) from exc
