"""
Voice layer.

Pluggable speech-to-text and text-to-speech:

    STT: OpenAISTT (Whisper API) · LocalWhisperSTT (free, offline)
    TTS: OpenAITTS · EdgeTTS (free) · GTTS (free)

Whisper auto-detects the spoken language and the TTS backends speak the reply
in that language, so the assistant works across languages (English, Russian,
Uzbek, …) with no per-language configuration.
"""

from jarvis.voice.base import BaseSTT, BaseTTS, Transcription, VoiceError
from jarvis.voice.service import VoiceService

__all__ = ["VoiceService", "Transcription", "VoiceError", "BaseSTT", "BaseTTS"]
