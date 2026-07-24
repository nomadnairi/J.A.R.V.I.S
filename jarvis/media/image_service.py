"""
Image generation via an OpenAI-compatible Images API (DALL·E / gpt-image-1).

Thin async wrapper: give it a prompt, get PNG bytes back. Kept separate from the
text LLM layer. Uses ``OPENAI_API_KEY`` by default (or a dedicated image key /
endpoint), so it works with the real OpenAI or any compatible image gateway.
"""

from __future__ import annotations

import base64

from jarvis.config.settings import Settings
from jarvis.utils.exceptions import JarvisError


class ImageError(JarvisError):
    """Raised when image generation fails."""


class ImageService:
    """Generate images from text prompts through an OpenAI-compatible API."""

    def __init__(self, api_key: str, *, model: str = "dall-e-3",
                size: str = "1024x1024", base_url: str = "") -> None:
        self.api_key = api_key
        self.model = model
        self.size = size
        self.base_url = base_url
        self._client = None

    @classmethod
    def from_settings(cls, settings: Settings) -> "ImageService":
        # A dedicated image key/endpoint wins; otherwise reuse the OpenAI creds.
        return cls(
            api_key=settings.image_api_key or settings.openai_api_key,
            model=settings.image_model,
            size=settings.image_size,
            base_url=settings.image_base_url or settings.openai_base_url,
        )

    def available(self) -> bool:
        return bool(self.api_key)

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover - env guard
            raise ImageError("The 'openai' package is required for images.") from exc
        self._client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url or None)
        return self._client

    async def generate(self, prompt: str) -> bytes:
        """Generate one image and return PNG bytes."""
        if not self.available():
            raise ImageError("No image API key configured.")
        if not (prompt or "").strip():
            raise ImageError("Empty prompt.")
        client = self._ensure_client()
        try:
            result = await client.images.generate(
                model=self.model,
                prompt=prompt,
                size=self.size,
                n=1,
                response_format="b64_json",
            )
        except Exception as exc:  # noqa: BLE001 - surface a clean error
            raise ImageError(f"Image generation failed: {exc}") from exc
        b64 = result.data[0].b64_json
        if not b64:
            raise ImageError("Image API returned no data.")
        return base64.b64decode(b64)
