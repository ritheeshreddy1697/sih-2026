from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.core.permissions import Permission
from app.models.enums import AccountStatus, InstitutionType, RoleCode


class RolePublic(BaseModel):
    code: RoleCode
    display_name: str


class InstitutionPublic(BaseModel):
    id: UUID
    name: str
    code: str
    institution_type: InstitutionType


class ProfilePublic(BaseModel):
    full_name: str
    phone: str | None
    designation: str | None


class UserPublic(BaseModel):
    id: UUID
    email: EmailStr
    status: AccountStatus
    roles: list[RolePublic]
    permissions: list[Permission]
    profile: ProfilePublic | None
    institution: InstitutionPublic | None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RegistrationRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role_code: RoleCode
    phone: str | None = Field(default=None, max_length=32)
    organisation_name: str | None = Field(default=None, max_length=255)
    industry: str | None = Field(default=None, max_length=160)
    website: str | None = Field(default=None, max_length=500)
    company_size: str | None = Field(default=None, max_length=80)
    company_description: str | None = Field(default=None, max_length=4000)
    headquarters: str | None = Field(default=None, max_length=255)
    registration_number: str | None = Field(default=None, max_length=120)
    consent_accepted: bool

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)


class RegistrationResponse(BaseModel):
    message: str
    status: AccountStatus


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetRequestResponse(BaseModel):
    message: str
    reset_token: str | None = None


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=32, max_length=512)
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)


class MessageResponse(BaseModel):
    message: str


class AuthorizationCheckResponse(BaseModel):
    authorized: bool
    role: RoleCode


class AccountDeletionCreate(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    reason: str | None = Field(default=None, max_length=1000)
    acknowledge_retention: bool

    @model_validator(mode="after")
    def retention_is_acknowledged(self) -> "AccountDeletionCreate":
        if not self.acknowledge_retention:
            raise ValueError("The statutory-record retention notice must be acknowledged")
        return self


class AccountDeletionComplete(BaseModel):
    resolution_note: str = Field(min_length=10, max_length=2000)


class AccountDeletionPublic(BaseModel):
    id: UUID
    user_id: UUID
    account_email: str
    account_name: str
    status: str
    reason: str | None
    requested_at: datetime
    scheduled_for: datetime
    cancelled_at: datetime | None
    completed_at: datetime | None
    resolution_note: str | None


def validate_password_strength(value: str) -> str:
    checks = (
        any(character.islower() for character in value),
        any(character.isupper() for character in value),
        any(character.isdigit() for character in value),
        any(not character.isalnum() for character in value),
    )
    if not all(checks):
        raise ValueError("Password must include upper, lower, number and symbol characters")
    return value
