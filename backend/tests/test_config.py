from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def production_values() -> dict[str, object]:
    return {
        "environment": "production",
        "api_docs_enabled": False,
        "refresh_cookie_secure": True,
        "backend_cors_origins": ["https://training.example.gov.in"],
        "allowed_hosts": ["training.example.gov.in", "127.0.0.1"],
        "frontend_public_url": "https://training.example.gov.in",
        "biometric_enabled": False,
    }


def test_production_reads_database_and_jwt_from_secret_files(tmp_path: Path) -> None:
    database_secret = tmp_path / "database_url"
    jwt_secret = tmp_path / "jwt_secret_key"
    biometric_secret = tmp_path / "biometric_encryption_key"
    database_secret.write_text(
        "postgresql+psycopg://ncct:local-test-value@db:5432/ncct_training",
        encoding="utf-8",
    )
    jwt_secret.write_text("a" * 64, encoding="utf-8")
    biometric_secret.write_text("b" * 64, encoding="utf-8")

    configured = Settings(
        **production_values(),
        database_url_file=str(database_secret),
        jwt_secret_key_file=str(jwt_secret),
        biometric_encryption_key_file=str(biometric_secret),
    )

    assert configured.database_url.endswith("@db:5432/ncct_training")
    assert configured.jwt_secret_key == "a" * 64
    assert configured.biometric_encryption_key == "b" * 64


def test_production_rejects_development_jwt_placeholder() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY must be replaced"):
        Settings(
            **production_values(),
            database_url="postgresql+psycopg://ncct:local-test-value@db:5432/ncct_training",
            jwt_secret_key="local-development-key-replace-before-deployment",
        )


def test_production_rejects_demo_face_provider_when_biometrics_are_enabled() -> None:
    values = production_values()
    values["biometric_enabled"] = True
    with pytest.raises(ValidationError, match="demo face provider"):
        Settings(
            **values,
            database_url="postgresql+psycopg://ncct:local-test-value@db:5432/ncct_training",
            jwt_secret_key="a" * 64,
            biometric_encryption_key="b" * 64,
        )
