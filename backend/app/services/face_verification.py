from __future__ import annotations

import io
import math
from dataclasses import dataclass
from typing import Protocol

from PIL import Image, ImageOps, ImageStat, UnidentifiedImageError

from app.models import BiometricChallengeType

Image.MAX_IMAGE_PIXELS = 8_000_000


class FaceCaptureError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid_capture") -> None:
        super().__init__(message)
        self.code = code


class LivenessCheckFailed(FaceCaptureError):
    def __init__(self, score: float) -> None:
        super().__init__(
            "The liveness movement was not detected. Request a new challenge and try again.",
            code="liveness_failed",
        )
        self.score = score


@dataclass(frozen=True)
class FaceCaptureAnalysis:
    embedding: tuple[float, ...]
    liveness_score: float
    quality_score: float


class FaceVerificationProvider(Protocol):
    name: str
    model_version: str
    is_demo: bool

    def analyze(
        self,
        frames: list[bytes],
        challenge_type: BiometricChallengeType,
    ) -> FaceCaptureAnalysis: ...

    def compare(self, enrolled: tuple[float, ...], candidate: tuple[float, ...]) -> float: ...


class DemoFaceVerificationProvider:
    """Development-only visual-template comparison with a basic motion challenge."""

    name = "demo_local_visual_template"
    model_version = "demo-v1"
    is_demo = True

    def __init__(self, *, liveness_threshold: float) -> None:
        self.liveness_threshold = liveness_threshold

    def analyze(
        self,
        frames: list[bytes],
        challenge_type: BiometricChallengeType,
    ) -> FaceCaptureAnalysis:
        if challenge_type != BiometricChallengeType.TURN_HEAD:
            raise FaceCaptureError("Unsupported liveness challenge")
        if len(frames) != 3:
            raise FaceCaptureError("Exactly three camera frames are required")

        images = [self._decode(frame) for frame in frames]
        motion_vectors = [self._grayscale_vector(image, 32) for image in images]
        liveness_score = max(
            self._mean_absolute_difference(first, second)
            for first, second in zip(motion_vectors, motion_vectors[1:], strict=False)
        )
        if liveness_score < self.liveness_threshold:
            raise LivenessCheckFailed(liveness_score)

        quality_score = sum(self._quality(image) for image in images) / len(images)
        if quality_score < 0.035:
            raise FaceCaptureError(
                "The camera image is too dark or lacks enough detail. Improve lighting and retry.",
                code="low_quality",
            )

        frame_embeddings = [self._embedding(image) for image in images]
        averaged = tuple(
            sum(values) / len(frame_embeddings) for values in zip(*frame_embeddings, strict=True)
        )
        return FaceCaptureAnalysis(
            embedding=self._normalize(averaged),
            liveness_score=round(liveness_score, 6),
            quality_score=round(quality_score, 6),
        )

    def compare(self, enrolled: tuple[float, ...], candidate: tuple[float, ...]) -> float:
        if not enrolled or len(enrolled) != len(candidate):
            raise FaceCaptureError("Stored face template is incompatible", code="template_error")
        similarity = sum(left * right for left, right in zip(enrolled, candidate, strict=True))
        return round(max(0.0, min(1.0, (similarity + 1.0) / 2.0)), 6)

    @staticmethod
    def _decode(content: bytes) -> Image.Image:
        try:
            with Image.open(io.BytesIO(content)) as image:
                image.load()
                if image.format not in {"JPEG", "PNG"}:
                    raise FaceCaptureError("Camera frames must be JPEG or PNG images")
                normalized = ImageOps.exif_transpose(image).convert("RGB")
        except (OSError, UnidentifiedImageError) as exc:
            raise FaceCaptureError("Camera frame could not be decoded") from exc
        if normalized.width < 160 or normalized.height < 120:
            raise FaceCaptureError("Camera frames must be at least 160 by 120 pixels")
        if normalized.width * normalized.height > 8_000_000:
            raise FaceCaptureError("Camera frame dimensions are too large")
        return normalized

    @classmethod
    def _grayscale_vector(cls, image: Image.Image, size: int) -> tuple[float, ...]:
        square = cls._center_square(image)
        grayscale = square.convert("L").resize((size, size), Image.Resampling.BILINEAR)
        return tuple(value / 255.0 for value in grayscale.tobytes())

    @classmethod
    def _embedding(cls, image: Image.Image) -> tuple[float, ...]:
        grayscale = cls._grayscale_vector(image, 16)
        mean = sum(grayscale) / len(grayscale)
        shape = cls._normalize(tuple(value - mean for value in grayscale))

        square = cls._center_square(image).resize((64, 64), Image.Resampling.BILINEAR)
        histogram = square.histogram()
        pixels = float(square.width * square.height)
        colour: list[float] = []
        for channel in range(3):
            channel_values = histogram[channel * 256 : (channel + 1) * 256]
            colour.extend(
                sum(channel_values[start : start + 32]) / pixels for start in range(0, 256, 32)
            )
        return cls._normalize((*shape, *colour))

    @staticmethod
    def _center_square(image: Image.Image) -> Image.Image:
        side = min(image.width, image.height)
        left = (image.width - side) // 2
        top = (image.height - side) // 2
        return image.crop((left, top, left + side, top + side))

    @classmethod
    def _quality(cls, image: Image.Image) -> float:
        grayscale = cls._center_square(image).convert("L").resize((64, 64))
        return min(1.0, float(ImageStat.Stat(grayscale).stddev[0]) / 64.0)

    @staticmethod
    def _mean_absolute_difference(
        first: tuple[float, ...], second: tuple[float, ...]
    ) -> float:
        return sum(abs(left - right) for left, right in zip(first, second, strict=True)) / len(
            first
        )

    @staticmethod
    def _normalize(values: tuple[float, ...]) -> tuple[float, ...]:
        magnitude = math.sqrt(sum(value * value for value in values))
        if magnitude <= 1e-12:
            return tuple(0.0 for _ in values)
        return tuple(value / magnitude for value in values)
