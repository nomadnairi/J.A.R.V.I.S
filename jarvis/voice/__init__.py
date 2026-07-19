"""
Voice layer.

Speech-to-text and text-to-speech via the OpenAI audio API. Whisper
auto-detects the spoken language, and OpenAI TTS speaks whatever language the
reply text is in, so the assistant works across languages (English, Russian,
Uzbek, …) with no per-language configuration.
"""

from jarvis.voice.service import Transcription, VoiceService

__all__ = ["VoiceService", "Transcription"]
