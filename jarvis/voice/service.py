"""
Voice service facade.

Selects speech-to-text and text-to-speech backends from configuration and
exposes a single small interface to the rest of the system. Backends range from
paid cloud quality (OpenAI) to free / offline engines (local Whisper, edge-tts,
gTTS).
"""

from __future__ import annotations

from jarvis.config.settings import Settings
from jarvis.utils.logger import get_logger
from jarvis.voice.base import BaseSTT, BaseTTS, Transcription, VoiceError

logger = get_logger(__name__)


def _make_stt(settings: Settings) -> BaseSTT:
    if settings.stt_backend == "local":
        from jarvis.voice.local_whisper import LocalWhisperSTT
        return LocalWhisperSTT(settings.local_whisper_model)
    from jarvis.voice.openai_backend import OpenAISTT
    return OpenAISTT(settings.openai_api_key, model=settings.stt_model)


def _make_tts(settings: Settings) -> BaseTTS:
    backend = settings.tts_backend
    if backend == "edge":
        from jarvis.voice.free_tts import EdgeTTS
        return EdgeTTS()
    if backend == "gtts":
        from jarvis.voice.free_tts import GTTS
        return GTTS()
    from jarvis.voice.openai_backend import OpenAITTS
    return OpenAITTS(settings.openai_api_key, model=settings.tts_model,
                    voice=settings.tts_voice)


class VoiceService:
    """Coordinates the configured STT and TTS backends."""

    def __init__(self, stt: BaseSTT, tts: BaseTTS) -> None:
        self.stt = stt
        self.tts = tts

    @classmethod
    def from_settings(cls, settings: Settings) -> "VoiceService":
        return cls(_make_stt(settings), _make_tts(settings))

    # -- availability -------------------------------------------------------

    def stt_available(self) -> bool:
        return self.stt.is_available()

    def tts_available(self) -> bool:
        return self.tts.is_available()

    # -- operations ---------------------------------------------------------

    async def transcribe(self, audio: bytes, filename: str = "voice.ogg") -> Transcription:
        return await self.stt.transcribe(audio, filename)

    async def synthesize(self, text: str, language: str | None = None) -> bytes:
        return await self.tts.synthesize(text, language)

    # -- output metadata ----------------------------------------------------

    @property
    def tts_is_voice_note(self) -> bool:
        return self.tts.is_voice_note

    @property
    def tts_ext(self) -> str:
        return self.tts.output_ext


__all__ = ["VoiceService", "Transcription", "VoiceError"]
