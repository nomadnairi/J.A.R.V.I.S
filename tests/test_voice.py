"""Tests for the voice layer (backends and facade; no network, no heavy deps)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from jarvis.config.settings import Settings
from jarvis.voice.base import BaseSTT, BaseTTS, Transcription, VoiceError
from jarvis.voice.languages import lang_code
from jarvis.voice.openai_backend import OpenAISTT, OpenAITTS
from jarvis.voice.service import VoiceService


# -- language codes ---------------------------------------------------------


def test_lang_code_from_name_and_code():
    assert lang_code("russian") == "ru"
    assert lang_code("uzbek") == "uz"
    assert lang_code("en") == "en"
    assert lang_code("ru-RU") == "ru"
    assert lang_code(None) == "en"


# -- fake OpenAI async client ----------------------------------------------


class _FakeTranscriptions:
    async def create(self, **kwargs):
        return SimpleNamespace(text="  привет мир  ", language="russian")


class _FakeStreamResponse:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def read(self):
        return b"OPUS_AUDIO_BYTES"


class _FakeStreaming:
    def create(self, **kwargs):
        return _FakeStreamResponse()


class _FakeClient:
    audio = SimpleNamespace(
        transcriptions=_FakeTranscriptions(),
        speech=SimpleNamespace(with_streaming_response=_FakeStreaming()),
    )


# -- OpenAI backends --------------------------------------------------------


@pytest.mark.asyncio
async def test_openai_stt_transcribe():
    stt = OpenAISTT("key")
    stt._client = _FakeClient()
    result = await stt.transcribe(b"audio")
    assert result.text == "привет мир"
    assert result.language == "russian"


@pytest.mark.asyncio
async def test_openai_tts_synthesize():
    tts = OpenAITTS("key")
    tts._client = _FakeClient()
    assert await tts.synthesize("hello") == b"OPUS_AUDIO_BYTES"
    assert tts.is_voice_note is True
    assert tts.output_ext == "ogg"


def test_openai_backends_availability():
    assert OpenAISTT("k").is_available() is True
    assert OpenAISTT("").is_available() is False
    assert OpenAITTS("").is_available() is False


@pytest.mark.asyncio
async def test_openai_stt_without_key_raises():
    with pytest.raises(VoiceError):
        await OpenAISTT("").transcribe(b"x")


# -- facade -----------------------------------------------------------------


class _FakeSTT(BaseSTT):
    async def transcribe(self, audio, filename="voice.ogg"):
        return Transcription(text="hi", language="english")


class _FakeTTS(BaseTTS):
    output_ext = "mp3"
    is_voice_note = False

    async def synthesize(self, text, language=None):
        return b"AUDIO"


@pytest.mark.asyncio
async def test_service_delegates():
    svc = VoiceService(_FakeSTT(), _FakeTTS())
    assert (await svc.transcribe(b"x")).text == "hi"
    assert await svc.synthesize("hello", "en") == b"AUDIO"
    assert svc.tts_is_voice_note is False
    assert svc.tts_ext == "mp3"


def test_from_settings_selects_backends():
    from jarvis.voice.free_tts import GTTS
    from jarvis.voice.local_whisper import LocalWhisperSTT

    svc = VoiceService.from_settings(
        Settings(stt_backend="local", tts_backend="gtts")
    )
    assert isinstance(svc.stt, LocalWhisperSTT)
    assert isinstance(svc.tts, GTTS)
    assert svc.tts_is_voice_note is False


def test_from_settings_defaults_to_openai():
    svc = VoiceService.from_settings(Settings(openai_api_key="k"))
    assert svc.stt.name == "openai"
    assert svc.tts.name == "openai"
