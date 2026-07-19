"""
Voice backend contracts.

Speech-to-text (:class:`BaseSTT`) and text-to-speech (:class:`BaseTTS`) are
pluggable so users can choose paid cloud quality (OpenAI) or free / offline
engines (local Whisper, edge-tts, gTTS) without touching the rest of the code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from jarvis.utils.exceptions import JarvisError


class VoiceError(JarvisError):
    """Raised when speech transcription or synthesis fails."""


@dataclass
class Transcription:
    """Result of transcribing an audio clip."""

    text: str
    language: str | None = None  # detected language (name or ISO code), if any


class BaseSTT(ABC):
    """Speech-to-text backend."""

    name: str = "base"

    @abstractmethod
    async def transcribe(self, audio: bytes, filename: str = "voice.ogg") -> Transcription:
        """Transcribe ``audio`` bytes into text (+ detected language)."""
        raise NotImplementedError

    def is_available(self) -> bool:
        return True


class BaseTTS(ABC):
    """Text-to-speech backend."""

    name: str = "base"
    #: File extension of the produced audio.
    output_ext: str = "ogg"
    #: Whether the output can be sent as a Telegram *voice note* (Opus/OGG).
    #: MP3 backends set this False and are sent as an audio file instead.
    is_voice_note: bool = True

    @abstractmethod
    async def synthesize(self, text: str, language: str | None = None) -> bytes:
        """Synthesise ``text`` into audio bytes (optionally for ``language``)."""
        raise NotImplementedError

    def is_available(self) -> bool:
        return True
