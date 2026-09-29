from __future__ import annotations

import re
import time
from collections import defaultdict
from threading import Lock
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core.config import settings

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,128}$")
SENSITIVE_AUTH_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/password-reset/request",
    "/api/v1/auth/password-reset/confirm",
    "/api/v1/attendance/biometrics/enrollment/challenge",
    "/api/v1/attendance/biometrics/enrollment",
    "/api/v1/attendance/kiosk/biometrics/challenge",
    "/api/v1/attendance/kiosk/biometrics/verify",
}


class RequestSecurityMiddleware(BaseHTTPMiddleware):
    """Applies bounded requests, process-level throttling, and browser security headers.

    The reverse proxy also rate limits requests in production. Keeping a conservative
    application limit protects direct/internal access and provides deterministic API errors.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._counts: defaultdict[tuple[str, str, int], int] = defaultdict(int)
        self._lock = Lock()
        self._requests_seen = 0

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = self._request_id(request)
        request.state.request_id = request_id
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > settings.max_request_size_bytes:
                    return self._secured(
                        JSONResponse(
                            {"detail": "Request body is too large", "request_id": request_id},
                            status_code=413,
                        ),
                        request_id,
                    )
            except ValueError:
                return self._secured(
                    JSONResponse(
                        {"detail": "Invalid Content-Length header", "request_id": request_id},
                        status_code=400,
                    ),
                    request_id,
                )

        retry_after = self._rate_limit(request)
        if retry_after is not None:
            return self._secured(
                JSONResponse(
                    {
                        "detail": "Too many requests. Please try again shortly.",
                        "request_id": request_id,
                    },
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                ),
                request_id,
            )

        response = await call_next(request)
        return self._secured(response, request_id)

    @staticmethod
    def _request_id(request: Request) -> str:
        supplied = request.headers.get("x-request-id", "")
        return supplied if REQUEST_ID_PATTERN.fullmatch(supplied) else str(uuid4())

    def _rate_limit(self, request: Request) -> int | None:
        if request.method == "OPTIONS" or not request.url.path.startswith("/api/"):
            return None
        now = int(time.time())
        window = now // 60
        client = request.client.host if request.client else "unknown"
        scope = "auth" if request.url.path in SENSITIVE_AUTH_PATHS else "api"
        limit = (
            settings.auth_rate_limit_per_minute
            if scope == "auth"
            else settings.api_rate_limit_per_minute
        )
        key = (scope, client, window)
        with self._lock:
            self._counts[key] += 1
            count = self._counts[key]
            self._requests_seen += 1
            if self._requests_seen % 500 == 0:
                self._counts = defaultdict(
                    int,
                    {item: value for item, value in self._counts.items() if item[2] >= window - 1},
                )
        return 60 - now % 60 if count > limit else None

    @staticmethod
    def _secured(response: Response, request_id: str) -> Response:
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(self), microphone=(), geolocation=(), payment=(), usb=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        if response.headers.get("content-type", "").startswith("application/json"):
            response.headers["Cache-Control"] = "no-store"
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
