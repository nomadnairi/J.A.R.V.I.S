"""
Free text-to-speech backends: edge-tts and gTTS.

* :class:`EdgeTTS` — Microsoft Edge's online neural voices via the free
  ``edge-tts`` package. High quality and multilingual (including Uzbek). No API
  key. Outputs MP3.
* :class:`GTTS` — Google Translate TTS via the free ``gTTS`` package. Simple
  and broadly multilingual. No API key. Outputs MP3.

Both are optional dependencies, imported lazily.
"""

from __future__ import annotations

import asyncio
from io import BytesIO

from jarvis.voice.base import BaseTTS, VoiceError
from jarvis.voice.languages import lang_code

# A neural Edge voice per language (falls back to English).
_EDGE_VOICES = {
    "en": "en-US-AriaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "uz": "uz-UZ-MadinaNeural",
    "kk": "kk-KZ-AigulNeural",
    "tr": "tr-TR-EmelNeural",
    "de": "de-DE-KatjaNeural",
    "fr": "fr-FR-DeniseNeural",
    "es": "es-ES-ElviraNeural",
}


class EdgeTTS(BaseTTS):
    """Free, multilingual TTS via Microsoft Edge (``edge-tts``)."""

    name = "edge"
    output_ext = "mp3"
    is_voice_note = False

    def __init__(self, default_voice: str = "en-US-AriaNeural") -> None:
        self.default_voice = default_voice

    def _voice_for(self, language: str | None) -> str:
        return _EDGE_VOICES.get(lang_code(language), self.default_voice)

    async def synthesize(self, text: str, language: str | None = None) -> bytes:
        if not text.strip():
            raise VoiceError("Nothing to synthesise.")
        try:
            import edge_tts
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise VoiceError(
                "EdgeTTS needs the 'edge-tts' package. Install it with: "
                "pip install edge-tts"
            ) from exc
        try:
            communicate = edge_tts.Communicate(text, self._voice_for(language))
            audio = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio.extend(chunk["data"])
        except Exception as exc:  # noqa: BLE001
            raise VoiceError(f"Edge TTS failed: {exc}") from exc
        return bytes(audio)


class GTTS(BaseTTS):
    """Free TTS via Google Translate (``gTTS``)."""

    name = "gtts"
    output_ext = "mp3"
    is_voice_note = False

    def _synthesize_sync(self, text: str, language: str | None) -> bytes:
        from gtts import gTTS  # imported here so the dep stays optional

        buffer = BytesIO()
        gTTS(text=text, lang=lang_code(language)).write_to_fp(buffer)
        return buffer.getvalue()

    async def synthesize(self, text: str, language: str | None = None) -> bytes:
        if not text.strip():
            raise VoiceError("Nothing to synthesise.")
        try:
            import gtts  # noqa: F401 - availability check
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise VoiceError(
                "gTTS needs the 'gTTS' package. Install it with: pip install gTTS"
            ) from exc
        try:
            return await asyncio.to_thread(self._synthesize_sync, text, language)
        except VoiceError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise VoiceError(f"gTTS failed: {exc}") from exc
