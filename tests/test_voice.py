"""Tests for the voice service (OpenAI client mocked — no network)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from jarvis.voice.service import Transcription, VoiceError, VoiceService


# -- fake OpenAI async client ----------------------------------------------


class _FakeTranscriptions:
    async def create(self, **kwargs):
        assert kwargs["model"] == "whisper-1"
        return SimpleNamespace(text="  привет мир  ", language="russian")


class _FakeStreamResponse:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def read(self):
        return b"OPUS_AUDIO_BYTES"


class _FakeStreaming:
    def create(self, **kwargs):  # returns an async context manager
        assert kwargs["voice"] == "alloy"
        return _FakeStreamResponse()


class _FakeSpeech:
    with_streaming_response = _FakeStreaming()


class _FakeClient:
    audio = SimpleNamespace(
        transcriptions=_FakeTranscriptions(),
        speech=_FakeSpeech(),
    )


def _service() -> VoiceService:
    svc = VoiceService("test-key")
    svc._client = _FakeClient()  # inject the fake, skip the real SDK
    return svc


# -- tests ------------------------------------------------------------------


def test_is_available():
    assert VoiceService("k").is_available() is True
    assert VoiceService("").is_available() is False


@pytest.mark.asyncio
async def test_transcribe_returns_text_and_language():
    result = await _service().transcribe(b"audio-bytes")
    assert isinstance(result, Transcription)
    assert result.text == "привет мир"  # trimmed
    assert result.language == "russian"


@pytest.mark.asyncio
async def test_synthesize_returns_audio_bytes():
    audio = await _service().synthesize("hello there")
    assert audio == b"OPUS_AUDIO_BYTES"


@pytest.mark.asyncio
async def test_transcribe_without_key_raises():
    with pytest.raises(VoiceError):
        await VoiceService("").transcribe(b"x")


@pytest.mark.asyncio
async def test_synthesize_empty_text_raises():
    with pytest.raises(VoiceError):
        await _service().synthesize("   ")


def test_from_settings():
    from jarvis.config.settings import Settings

    svc = VoiceService.from_settings(
        Settings(openai_api_key="k", tts_voice="verse")
    )
    assert svc.tts_voice == "verse"
