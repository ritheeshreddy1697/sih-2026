from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import AuthContext, require_permission
from app.core.config import settings
from app.core.permissions import Permission
from app.core.uploads import FACE_IMAGE_TYPES, read_validated_upload
from app.db.session import get_db
from app.models import KioskDevice
from app.schemas.attendance import (
    AttendanceCorrectionCreate,
    AttendanceCorrectionPublic,
    AttendanceCorrectionReview,
    AttendanceReportPublic,
    AttendanceSessionCreate,
    AttendanceSessionPublic,
    AttendanceSessionUpdate,
    BiometricChallengePublic,
    BiometricEnrollmentPublic,
    BiometricReviewRequest,
    BiometricVerificationPublic,
    CheckInSyncRequest,
    CheckInSyncResponse,
    KioskBiometricChallengeCreate,
    KioskDeviceCreate,
    KioskDevicePublic,
    KioskDeviceRegistered,
    KioskPairRequest,
    KioskSessionPublic,
    MessagePublic,
    SessionQrPublic,
    SessionTraineePublic,
    TraineeIdentityPublic,
)
from app.services import attendance as attendance_service
from app.services import biometrics as biometric_service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


def get_kiosk_device(
    db: DbSession,
    kiosk_token: Annotated[str | None, Header(alias="X-Kiosk-Token")] = None,
) -> KioskDevice:
    return attendance_service.authenticate_device(db, kiosk_token)


KioskAuth = Annotated[KioskDevice, Depends(get_kiosk_device)]


async def read_face_frames(frames: list[UploadFile]) -> list[bytes]:
    if len(frames) != 3:
        raise HTTPException(status_code=422, detail="Exactly three camera frames are required")
    result: list[bytes] = []
    for frame in frames:
        content, _, _ = await read_validated_upload(
            frame,
            allowed_types=FACE_IMAGE_TYPES,
            maximum_bytes=settings.biometric_frame_max_bytes,
            kind="camera frame",
        )
        result.append(content)
    return result


@router.get("/identity/me", response_model=TraineeIdentityPublic)
def get_my_attendance_identity(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ATTENDANCE_SELF))],
) -> TraineeIdentityPublic:
    return attendance_service.identity_public(db, auth.user)


@router.get("/biometrics/enrollment/me", response_model=BiometricEnrollmentPublic)
def get_my_biometric_enrollment(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ATTENDANCE_SELF))],
) -> BiometricEnrollmentPublic:
    return biometric_service.enrollment_public(db, auth.user)


@router.post(
    "/biometrics/enrollment/challenge",
    response_model=BiometricChallengePublic,
    status_code=201,
)
def create_biometric_enrollment_challenge(
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ATTENDANCE_SELF))],
) -> BiometricChallengePublic:
    return biometric_service.issue_enrollment_challenge(db, request, auth.user)


@router.post("/biometrics/enrollment", response_model=BiometricEnrollmentPublic)
async def enroll_biometric_template(
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ATTENDANCE_SELF))],
    challenge_id: Annotated[UUID, Form()],
    consent_granted: Annotated[bool, Form()],
    frames: Annotated[list[UploadFile], File()],
) -> BiometricEnrollmentPublic:
    return biometric_service.enroll(
        db,
        request,
        auth.user,
        challenge_id=challenge_id,
        consent_granted=consent_granted,
        frames=await read_face_frames(frames),
    )


@router.delete("/biometrics/enrollment/me", response_model=MessagePublic)
def delete_my_biometric_enrollment(
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ATTENDANCE_SELF))],
) -> MessagePublic:
    message = biometric_service.delete_enrollment(db, request, auth.user, auth.user)
    return MessagePublic(message=message)


@router.delete("/biometrics/enrollments/{trainee_id}", response_model=MessagePublic)
def delete_trainee_biometric_enrollment(
    trainee_id: UUID,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ATTENDANCE_APPROVE))],
) -> MessagePublic:
    trainee = biometric_service.load_trainee_for_admin(db, trainee_id)
    message = biometric_service.delete_enrollment(db, request, auth.user, trainee)
    return MessagePublic(message=message)


@router.get("/biometrics/reviews", response_model=list[BiometricVerificationPublic])
def get_biometric_manual_reviews(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ATTENDANCE_APPROVE))],
) -> list[BiometricVerificationPublic]:
    return biometric_service.list_manual_reviews(db, auth.user)


@router.patch(
    "/biometrics/reviews/{verification_id}",
    response_model=BiometricVerificationPublic,
)
def review_biometric_verification(
    verification_id: UUID,
    payload: BiometricReviewRequest,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ATTENDANCE_APPROVE))],
) -> BiometricVerificationPublic:
    return biometric_service.review_verification(
        db, request, auth.user, verification_id, payload
    )


@router.get("/sessions", response_model=list[AttendanceSessionPublic])
def get_attendance_sessions(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ATTENDANCE_MANAGE))],
) -> list[AttendanceSessionPublic]:
    return attendance_service.list_sessions(db, auth.user)


@router.post("/sessions", response_model=AttendanceSessionPublic, status_code=201)
def create_attendance_session(
    payload: AttendanceSessionCreate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ATTENDANCE_MANAGE))],
) -> AttendanceSessionPublic:
    item = attendance_service.create_session(db, request, auth.user, payload)
    return attendance_service.session_public(item)


@router.patch("/sessions/{session_id}", response_model=AttendanceSessionPublic)
def update_attendance_session(
    session_id: UUID,
    payload: AttendanceSessionUpdate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ATTENDANCE_MANAGE))],
) -> AttendanceSessionPublic:
    item = attendance_service.load_session(db, session_id)
    updated = attendance_service.update_session(db, request, auth.user, item, payload)
    return attendance_service.session_public(updated)


@router.get("/sessions/{session_id}/qr", response_model=SessionQrPublic)
def get_session_qr(
    session_id: UUID,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ATTENDANCE_MANAGE))],
) -> SessionQrPublic:
    item = attendance_service.load_session(db, session_id)
    return attendance_service.session_qr(db, auth.user, item)


@router.get("/sessions/{session_id}/trainees", response_model=list[SessionTraineePublic])
def get_session_trainees(
    session_id: UUID,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ATTENDANCE_MANAGE))],
) -> list[SessionTraineePublic]:
    item = attendance_service.load_session(db, session_id)
    return attendance_service.session_trainees(db, auth.user, item)


@router.get("/sessions/{session_id}/report", response_model=AttendanceReportPublic)
def get_attendance_report(
    session_id: UUID,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ATTENDANCE_REPORTS))],
) -> AttendanceReportPublic:
    item = attendance_service.load_session(db, session_id)
    return attendance_service.attendance_report(db, auth.user, item)


@router.post(
    "/sessions/{session_id}/corrections",
    response_model=AttendanceCorrectionPublic,
    status_code=201,
)
def request_attendance_correction(
    session_id: UUID,
    payload: AttendanceCorrectionCreate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ATTENDANCE_MANAGE))],
) -> AttendanceCorrectionPublic:
    session_item = attendance_service.load_session(db, session_id)
    correction = attendance_service.request_correction(
        db, request, auth.user, session_item, payload
    )
    return attendance_service.correction_public(correction)


@router.get("/corrections", response_model=list[AttendanceCorrectionPublic])
def get_attendance_corrections(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ATTENDANCE_MANAGE))],
) -> list[AttendanceCorrectionPublic]:
    return attendance_service.list_corrections(db, auth.user)


@router.patch("/corrections/{correction_id}", response_model=AttendanceCorrectionPublic)
def review_attendance_correction(
    correction_id: UUID,
    payload: AttendanceCorrectionReview,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ATTENDANCE_APPROVE))],
) -> AttendanceCorrectionPublic:
    correction = attendance_service.review_correction(
        db, request, auth.user, correction_id, payload
    )
    return attendance_service.correction_public(correction)


@router.get("/devices", response_model=list[KioskDevicePublic])
def get_kiosk_devices(
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ATTENDANCE_MANAGE))],
) -> list[KioskDevicePublic]:
    return attendance_service.list_devices(db, auth.user)


@router.post("/devices", response_model=KioskDeviceRegistered, status_code=201)
def register_kiosk_device(
    payload: KioskDeviceCreate,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ATTENDANCE_MANAGE))],
) -> KioskDeviceRegistered:
    return attendance_service.register_device(db, request, auth.user, payload)


@router.post("/devices/{device_id}/revoke", response_model=KioskDevicePublic)
def revoke_kiosk_device(
    device_id: UUID,
    request: Request,
    db: DbSession,
    auth: Annotated[AuthContext, Depends(require_permission(Permission.ATTENDANCE_MANAGE))],
) -> KioskDevicePublic:
    return attendance_service.revoke_device(db, request, auth.user, device_id)


@router.post("/kiosk/pair", response_model=KioskSessionPublic)
def pair_kiosk_session(
    payload: KioskPairRequest,
    request: Request,
    db: DbSession,
    device: KioskAuth,
) -> KioskSessionPublic:
    return attendance_service.pair_session(db, request, device, payload.session_qr)


@router.post("/kiosk/check-ins/sync", response_model=CheckInSyncResponse)
def synchronize_kiosk_check_ins(
    payload: CheckInSyncRequest,
    request: Request,
    db: DbSession,
    device: KioskAuth,
) -> CheckInSyncResponse:
    return attendance_service.sync_check_ins(db, request, device, payload.items)


@router.post(
    "/kiosk/biometrics/challenge",
    response_model=BiometricChallengePublic,
    status_code=201,
)
def create_kiosk_biometric_challenge(
    payload: KioskBiometricChallengeCreate,
    request: Request,
    db: DbSession,
    device: KioskAuth,
) -> BiometricChallengePublic:
    return biometric_service.issue_kiosk_challenge(db, request, device, payload)


@router.post("/kiosk/biometrics/verify", response_model=BiometricVerificationPublic)
async def verify_kiosk_biometric_capture(
    request: Request,
    db: DbSession,
    device: KioskAuth,
    challenge_id: Annotated[UUID, Form()],
    idempotency_key: Annotated[UUID, Form()],
    captured_at: Annotated[datetime, Form()],
    frames: Annotated[list[UploadFile], File()],
) -> BiometricVerificationPublic:
    return biometric_service.verify_kiosk_capture(
        db,
        request,
        device,
        challenge_id=challenge_id,
        idempotency_key=idempotency_key,
        captured_at=captured_at,
        frames=await read_face_frames(frames),
    )
