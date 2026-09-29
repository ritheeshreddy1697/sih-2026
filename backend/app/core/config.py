from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "NCCT Cooperative Training Platform API"
    environment: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    api_docs_enabled: bool = True
    database_url: str = (
        "postgresql+psycopg://ncct:change-me-local-only@localhost:5432/ncct_training"
    )
    database_url_file: str | None = None
    backend_cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    allowed_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    max_request_size_bytes: int = Field(default=55 * 1024 * 1024, ge=1024, le=100 * 1024 * 1024)
    api_rate_limit_per_minute: int = Field(default=300, ge=10, le=10000)
    auth_rate_limit_per_minute: int = Field(default=10, ge=2, le=100)
    jwt_secret_key: str = "local-development-key-replace-before-deployment"
    jwt_secret_key_file: str | None = None
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_issuer: str = "ncct-training-platform"
    jwt_audience: str = "ncct-training-platform-users"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    password_reset_expire_minutes: int = 30
    refresh_cookie_name: str = "ncct_refresh_token"
    refresh_cookie_secure: bool = False
    seed_demo_password: str = "DemoOnly!2026"
    frontend_public_url: str = "http://localhost:5173"
    career_ai_provider: Literal["auto", "local", "gemini"] = "auto"
    gemini_api_key: str | None = None
    gemini_api_key_file: str | None = None
    gemini_model: str = "gemini-3.5-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    career_ai_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    career_chat_rate_limit_per_minute: int = Field(default=12, ge=1, le=100)
    career_chat_max_input_chars: int = Field(default=2000, ge=100, le=2000)
    account_deletion_cooling_days: int = Field(default=30, ge=1, le=90)
    biometric_enabled: bool = True
    face_verification_provider: str = "demo"
    biometric_encryption_key: str = "local-biometric-key-replace-before-deployment"
    biometric_encryption_key_file: str | None = None
    biometric_encryption_key_version: str = "v1"
    biometric_match_threshold: float = Field(default=0.90, ge=0.5, le=0.999)
    biometric_manual_review_threshold: float = Field(default=0.75, ge=0.25, le=0.99)
    biometric_liveness_threshold: float = Field(default=0.025, ge=0.001, le=0.5)
    biometric_challenge_expire_seconds: int = Field(default=120, ge=30, le=300)
    biometric_frame_max_bytes: int = Field(default=2 * 1024 * 1024, ge=100_000, le=5_000_000)

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        for value_field, file_field in (
            ("database_url", "database_url_file"),
            ("jwt_secret_key", "jwt_secret_key_file"),
            ("gemini_api_key", "gemini_api_key_file"),
            ("biometric_encryption_key", "biometric_encryption_key_file"),
        ):
            secret_path = getattr(self, file_field)
            if secret_path:
                try:
                    value = Path(secret_path).read_text(encoding="utf-8").strip()
                except OSError as exc:
                    raise ValueError(f"Unable to read {file_field.upper()}") from exc
                if not value:
                    raise ValueError(f"{file_field.upper()} cannot be empty")
                object.__setattr__(self, value_field, value)
        if self.environment == "production":
            if self.jwt_secret_key == "local-development-key-replace-before-deployment":
                raise ValueError("JWT_SECRET_KEY must be replaced in production")
            if len(self.jwt_secret_key) < 32:
                raise ValueError("JWT_SECRET_KEY must contain at least 32 characters")
            if not self.refresh_cookie_secure:
                raise ValueError("REFRESH_COOKIE_SECURE must be enabled in production")
            if self.api_docs_enabled:
                raise ValueError("API_DOCS_ENABLED must be disabled in production")
            if "change-me" in self.database_url or not self.database_url.startswith(
                ("postgresql://", "postgresql+psycopg://")
            ):
                raise ValueError(
                    "DATABASE_URL must use PostgreSQL with non-placeholder credentials"
                )
            if not self.backend_cors_origins or any(
                origin == "*" or not origin.startswith("https://")
                for origin in self.backend_cors_origins
            ):
                raise ValueError("Production CORS origins must be explicit HTTPS origins")
            if not self.allowed_hosts or "*" in self.allowed_hosts:
                raise ValueError("Production ALLOWED_HOSTS must be explicit")
            if not self.frontend_public_url.startswith("https://"):
                raise ValueError("FRONTEND_PUBLIC_URL must use HTTPS in production")
            if self.biometric_enabled:
                if self.face_verification_provider == "demo":
                    raise ValueError(
                        "The demo face provider cannot be enabled in production"
                    )
                if (
                    self.biometric_encryption_key
                    == "local-biometric-key-replace-before-deployment"
                    or len(self.biometric_encryption_key) < 32
                ):
                    raise ValueError(
                        "BIOMETRIC_ENCRYPTION_KEY must be a separate strong secret"
                    )
        if self.biometric_manual_review_threshold >= self.biometric_match_threshold:
            raise ValueError(
                "BIOMETRIC_MANUAL_REVIEW_THRESHOLD must be below BIOMETRIC_MATCH_THRESHOLD"
            )
        return self

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]

        return value

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [host.strip() for host in value.split(",") if host.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
