"""OpenAI speech backends (Whisper API STT, OpenAI TTS)."""

from __future__ import annotations

from jarvis.voice.base import BaseSTT, BaseTTS, Transcription, VoiceError


class OpenAISTT(BaseSTT):
    """Speech-to-text via the OpenAI Whisper API (cloud, paid)."""

    name = "openai"

    def __init__(self, api_key: str, model: str = "whisper-1") -> None:
        self.api_key = api_key
        self.model = model
        self._client: object | None = None

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _ensure_client(self) -> object:
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as exc:  # pragma: no cover - env guard
                raise VoiceError("The 'openai' package is required.") from exc
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def transcribe(self, audio: bytes, filename: str = "voice.ogg") -> Transcription:
        if not self.api_key:
            raise VoiceError("Missing OpenAI API key for transcription.")
        client = self._ensure_client()
        try:
            response = await client.audio.transcriptions.create(  # type: ignore[attr-defined]
                model=self.model,
                file=(filename, audio),
                response_format="verbose_json",
            )
        except Exception as exc:  # noqa: BLE001
            raise VoiceError(f"Transcription failed: {exc}") from exc
        return Transcription(
            text=(getattr(response, "text", "") or "").strip(),
            language=getattr(response, "language", None),
        )


class OpenAITTS(BaseTTS):
    """Text-to-speech via the OpenAI TTS API (cloud, paid). Outputs Opus."""

    name = "openai"
    output_ext = "ogg"
    is_voice_note = True

    def __init__(self, api_key: str, model: str = "tts-1", voice: str = "alloy") -> None:
        self.api_key = api_key
        self.model = model
        self.voice = voice
        self._client: object | None = None

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _ensure_client(self) -> object:
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as exc:  # pragma: no cover - env guard
                raise VoiceError("The 'openai' package is required.") from exc
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def synthesize(self, text: str, language: str | None = None) -> bytes:
        if not self.api_key:
            raise VoiceError("Missing OpenAI API key for speech synthesis.")
        if not text.strip():
            raise VoiceError("Nothing to synthesise.")
        client = self._ensure_client()
        try:
            async with client.audio.speech.with_streaming_response.create(  # type: ignore[attr-defined]
                model=self.model,
                voice=self.voice,
                input=text,
                response_format="opus",
            ) as response:
                return await response.read()
        except Exception as exc:  # noqa: BLE001
            raise VoiceError(f"Speech synthesis failed: {exc}") from exc
