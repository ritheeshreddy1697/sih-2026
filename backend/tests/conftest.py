from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.session import get_db
from app.main import create_app
from app.models import AccountStatus, Base, Institution, Role, RoleCode, User, UserProfile


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with testing_session() as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_test_user(
    db: Session,
    *,
    email: str,
    password: str = "DemoOnly!2026",
    role_code: RoleCode = RoleCode.TRAINEE,
    status: AccountStatus = AccountStatus.ACTIVE,
    institution: Institution | None = None,
) -> User:
    role = db.scalar(select(Role).where(Role.code == role_code))
    if role is None:
        role = Role(code=role_code, display_name=role_code.value.replace("_", " ").title())
    user = User(
        email=email,
        password_hash=hash_password(password),
        status=status,
        email_verified_at=datetime.now(UTC) if status == AccountStatus.ACTIVE else None,
        roles=[role],
        profile=UserProfile(full_name="Test User"),
        institution=institution,
    )
    db.add(user)
    db.commit()
    return user
