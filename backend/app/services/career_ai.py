from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.models.enums import CareerLanguage


@dataclass(frozen=True)
class GroundingSource:
    key: str
    title: str
    content: str
    url: str


@dataclass(frozen=True)
class ProviderMessage:
    role: str
    content: str


@dataclass(frozen=True)
class CareerAIRequest:
    language: CareerLanguage
    intent: str
    message: str
    history: list[ProviderMessage]
    sources: list[GroundingSource]


class CareerAIError(RuntimeError):
    pass


class CareerAIProvider(Protocol):
    name: str

    def generate(self, request: CareerAIRequest) -> str: ...


LANGUAGE_NAMES = {
    CareerLanguage.ENGLISH: "English",
    CareerLanguage.HINDI: "Hindi",
    CareerLanguage.TELUGU: "Telugu",
}


class LocalFaqProvider:
    name = "local-faq"

    def generate(self, request: CareerAIRequest) -> str:
        if request.sources:
            return request.sources[0].content
        return {
            CareerLanguage.ENGLISH: (
                "I do not have approved platform information for that question. "
                "Please try a programme, job, resume or interview question, or contact support."
            ),
            CareerLanguage.HINDI: (
                "इस प्रश्न के लिए मेरे पास स्वीकृत प्लेटफ़ॉर्म जानकारी उपलब्ध नहीं है। "
                "कृपया कार्यक्रम, नौकरी, रिज़्यूमे या साक्षात्कार से जुड़ा प्रश्न पूछें, "
                "या सहायता टीम से संपर्क करें।"
            ),
            CareerLanguage.TELUGU: (
                "ఈ ప్రశ్నకు ఆమోదించబడిన ప్లాట్‌ఫారమ్ సమాచారం నా వద్ద లేదు. "
                "దయచేసి శిక్షణ, ఉద్యోగం, రెజ్యూమే లేదా ఇంటర్వ్యూ గురించి అడగండి, "
                "లేదా సహాయక బృందాన్ని సంప్రదించండి."
            ),
        }[request.language]


class GeminiCompatibleProvider:
    name = "gemini-compatible"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def generate(self, request: CareerAIRequest) -> str:
        source_text = "\n\n".join(
            f"[{source.key}] {source.title}\n{source.content}\nPlatform URL: {source.url}"
            for source in request.sources
        )
        system_instruction = (
            "You are the NCCT trainee career counsellor. Answer only from the approved "
            "sources below. Never create a job, scheme, programme, eligibility rule, deadline, "
            "salary, or benefit. If the sources do not answer the question, clearly say the "
            "information is unavailable. Keep the answer practical and concise. Cite relevant "
            "sources using their exact bracketed keys, and do not add external links. "
            f"Reply in {LANGUAGE_NAMES[request.language]}.\n\nAPPROVED SOURCES:\n"
            f"{source_text or 'No approved sources were retrieved.'}"
        )
        contents = [
            {
                "role": "model" if item.role == "assistant" else "user",
                "parts": [{"text": item.content}],
            }
            for item in request.history[-8:]
        ]
        contents.append({"role": "user", "parts": [{"text": request.message}]})
        url = f"{self._base_url}/models/{quote(self._model, safe='')}:generateContent"
        try:
            response = httpx.post(
                url,
                headers={"x-goog-api-key": self._api_key},
                json={
                    "system_instruction": {"parts": [{"text": system_instruction}]},
                    "contents": contents,
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 700,
                    },
                },
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            parts = payload["candidates"][0]["content"]["parts"]
            answer = "".join(str(part.get("text", "")) for part in parts).strip()
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise CareerAIError(
                "The configured AI provider did not return a usable answer"
            ) from exc
        if not answer:
            raise CareerAIError("The configured AI provider returned an empty answer")
        return answer


@lru_cache
def get_career_ai_provider() -> CareerAIProvider:
    if settings.career_ai_provider in {"auto", "gemini"} and settings.gemini_api_key:
        return GeminiCompatibleProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            base_url=settings.gemini_base_url,
            timeout_seconds=settings.career_ai_timeout_seconds,
        )
    return LocalFaqProvider()
