from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


@dataclass(frozen=True)
class EncryptedBiometricTemplate:
    ciphertext: bytes
    nonce: bytes
    key_version: str


def _key() -> bytes:
    return hashlib.sha256(settings.biometric_encryption_key.encode("utf-8")).digest()


def _associated_data(
    trainee_id: UUID,
    provider_name: str,
    model_version: str,
    key_version: str,
) -> bytes:
    return (
        f"ncct-face-template:{trainee_id}:{provider_name}:{model_version}:{key_version}"
    ).encode()


def encrypt_embedding(
    embedding: tuple[float, ...],
    *,
    trainee_id: UUID,
    provider_name: str,
    model_version: str,
) -> EncryptedBiometricTemplate:
    key_version = settings.biometric_encryption_key_version
    nonce = os.urandom(12)
    plaintext = json.dumps(embedding, separators=(",", ":")).encode("utf-8")
    ciphertext = AESGCM(_key()).encrypt(
        nonce,
        plaintext,
        _associated_data(trainee_id, provider_name, model_version, key_version),
    )
    return EncryptedBiometricTemplate(ciphertext, nonce, key_version)


def decrypt_embedding(
    ciphertext: bytes,
    nonce: bytes,
    *,
    trainee_id: UUID,
    provider_name: str,
    model_version: str,
    key_version: str,
) -> tuple[float, ...]:
    if key_version != settings.biometric_encryption_key_version:
        raise RuntimeError("Biometric encryption key version is unavailable")
    try:
        plaintext = AESGCM(_key()).decrypt(
            nonce,
            ciphertext,
            _associated_data(trainee_id, provider_name, model_version, key_version),
        )
        values = json.loads(plaintext)
    except (InvalidTag, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Biometric template could not be decrypted") from exc
    if not isinstance(values, list) or not values:
        raise RuntimeError("Biometric template is invalid")
    try:
        return tuple(float(value) for value in values)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Biometric template is invalid") from exc
