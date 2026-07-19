"""
Voice service — OpenAI speech-to-text and text-to-speech.

Wraps the OpenAI audio API behind a small async interface so the rest of the
system never touches the SDK directly. The OpenAI client is imported lazily;
voice is an optional capability that only needs the ``openai`` package and an
API key.
"""

from __future__ import annotations

from dataclasses import dataclass

from jarvis.config.settings import Settings
from jarvis.utils.exceptions import JarvisError
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class VoiceError(JarvisError):
    """Raised when speech transcription or synthesis fails."""


@dataclass
class Transcription:
    """Result of transcribing an audio clip."""

    text: str
    language: str | None = None  # Whisper-detected language, if available


class VoiceService:
    """Speech-to-text (Whisper) and text-to-speech (OpenAI TTS)."""

    def __init__(
        self,
        api_key: str,
        *,
        stt_model: str = "whisper-1",
        tts_model: str = "tts-1",
        tts_voice: str = "alloy",
    ) -> None:
        self.api_key = api_key
        self.stt_model = stt_model
        self.tts_model = tts_model
        self.tts_voice = tts_voice
        self._client: object | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> "VoiceService":
        return cls(
            settings.openai_api_key,
            stt_model=settings.stt_model,
            tts_model=settings.tts_model,
            tts_voice=settings.tts_voice,
        )

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _ensure_client(self) -> object:
        if self._client is not None:
            return self._client
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover - env guard
            raise VoiceError(
                "The 'openai' package is required for voice. Run: pip install openai"
            ) from exc
        self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    # -- speech-to-text -----------------------------------------------------

    async def transcribe(self, audio: bytes, filename: str = "voice.ogg") -> Transcription:
        """Transcribe ``audio`` bytes, returning text and detected language."""
        if not self.api_key:
            raise VoiceError("Missing OpenAI API key for transcription.")
        client = self._ensure_client()
        try:
            response = await client.audio.transcriptions.create(  # type: ignore[attr-defined]
                model=self.stt_model,
                file=(filename, audio),
                response_format="verbose_json",
            )
        except Exception as exc:  # noqa: BLE001
            raise VoiceError(f"Transcription failed: {exc}") from exc
        return Transcription(
            text=(getattr(response, "text", "") or "").strip(),
            language=getattr(response, "language", None),
        )

    # -- text-to-speech -----------------------------------------------------

    async def synthesize(self, text: str, *, response_format: str = "opus") -> bytes:
        """Synthesise ``text`` into spoken audio (Opus by default)."""
        if not self.api_key:
            raise VoiceError("Missing OpenAI API key for speech synthesis.")
        if not text.strip():
            raise VoiceError("Nothing to synthesise.")
        client = self._ensure_client()
        try:
            async with client.audio.speech.with_streaming_response.create(  # type: ignore[attr-defined]
                model=self.tts_model,
                voice=self.tts_voice,
                input=text,
                response_format=response_format,
            ) as response:
                return await response.read()
        except Exception as exc:  # noqa: BLE001
            raise VoiceError(f"Speech synthesis failed: {exc}") from exc
