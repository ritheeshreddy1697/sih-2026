import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.middleware import RequestSecurityMiddleware
from app.schemas.health import HealthResponse


def create_app() -> FastAPI:
    docs_enabled = settings.api_docs_enabled and settings.environment != "production"
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs" if docs_enabled else None,
        redoc_url=None,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json" if docs_enabled else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "X-Request-ID",
            "X-Kiosk-Token",
        ],
        expose_headers=["Content-Disposition", "X-Request-ID", "Retry-After"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    app.add_middleware(RequestSecurityMiddleware)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None) or request.headers.get(
            "x-request-id"
        )
        errors = [
            {key: value for key, value in error.items() if key not in {"input", "ctx"}}
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={"detail": errors, "request_id": request_id},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = request.headers.get("x-request-id") or "generated-by-middleware"
        logging.getLogger("app.errors").exception(
            "Unhandled API error request_id=%s path=%s",
            request_id,
            request.url.path,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An unexpected error occurred",
                "request_id": request_id,
            },
        )

    @app.get("/health", tags=["health"])
    def root_health() -> HealthResponse:
        return HealthResponse(status="ok", service=settings.app_name)

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
