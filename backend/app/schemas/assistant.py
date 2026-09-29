from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import CareerLanguage


class AssistantHistoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def clean_content(cls, value: str) -> str:
        return " ".join(value.split())


class AssistantChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=2, max_length=2000)
    history: list[AssistantHistoryItem] = Field(default_factory=list, max_length=8)
    page_path: str = Field(default="/dashboard", min_length=1, max_length=200)
    language: CareerLanguage = CareerLanguage.ENGLISH

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Message must contain at least two characters")
        return cleaned

    @field_validator("page_path")
    @classmethod
    def clean_page_path(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith("/"):
            raise ValueError("Page path must be relative to this application")
        return cleaned


class AssistantChatResponse(BaseModel):
    answer: str
    provider: str
    used_local_fallback: bool
