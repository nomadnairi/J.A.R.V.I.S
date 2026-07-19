"""Tests for the desktop voice-turn controller (no GUI, fake voice/engine)."""

from __future__ import annotations

import threading

import pytest

from jarvis.config.settings import Settings
from jarvis.core.container import ServiceContainer
from jarvis.core.engine import JarvisEngine
from jarvis.desktop_app.engine_thread import EngineThread
from jarvis.desktop_app.voice_controller import VoiceController
from jarvis.llm.client import LLMClient
from jarvis.voice.base import Transcription
from tests.conftest import FakeProvider


class FakeVoice:
    """Stands in for VoiceService."""

    def __init__(self, text: str = "hello there", *, tts_ok: bool = True,
                stt_ok: bool = True):
        self._text = text
        self._tts_ok = tts_ok
        self._stt_ok = stt_ok
        self.synthesized: list[str] = []
        self.tts_ext = "mp3"

    def stt_available(self) -> bool:
        return self._stt_ok

    def tts_available(self) -> bool:
        return self._tts_ok

    async def transcribe(self, audio: bytes, filename: str = "voice.ogg"):
        return Transcription(text=self._text, language="en")

    async def synthesize(self, text: str, language=None) -> bytes:
        self.synthesized.append(text)
        return b"AUDIO"


@pytest.fixture()
def engine_thread():
    settings = Settings(
        anthropic_api_key="k", log_file="", memory_enabled=False,
        integrations_enabled=False, goals_enabled=False, rate_limit_enabled=False,
    )
    thread = EngineThread(settings)

    def _run_with_fake():
        import asyncio
        thread._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(thread._loop)
        thread._engine = JarvisEngine(container=ServiceContainer(
            settings, llm_client=LLMClient(primary=FakeProvider())))
        thread._loop.run_until_complete(thread._engine.start())
        thread._started.set()
        thread._loop.run_forever()
        thread._loop.run_until_complete(thread._engine.shutdown())
        thread._loop.close()

    thread._thread = threading.Thread(target=_run_with_fake, daemon=True)
    thread.start()
    yield thread
    thread.stop()


def test_full_voice_turn_with_tts(engine_thread):
    voice = FakeVoice()
    controller = VoiceController(voice, engine_thread)
    turn = controller.run_turn(b"WAVDATA")
    assert turn.transcript == "hello there"
    assert turn.reply == "Certainly, Sir."
    assert turn.reply_audio == b"AUDIO"
    assert turn.reply_audio_ext == "mp3"
    assert voice.synthesized == ["Certainly, Sir."]


def test_voice_turn_without_tts(engine_thread):
    controller = VoiceController(FakeVoice(tts_ok=False), engine_thread)
    turn = controller.run_turn(b"WAVDATA")
    assert turn.reply == "Certainly, Sir."
    assert turn.reply_audio is None


def test_speak_replies_off_skips_tts(engine_thread):
    voice = FakeVoice()
    controller = VoiceController(voice, engine_thread, speak_replies=False)
    turn = controller.run_turn(b"WAVDATA")
    assert turn.reply_audio is None
    assert voice.synthesized == []


def test_empty_transcript_short_circuits(engine_thread):
    controller = VoiceController(FakeVoice(text="   "), engine_thread)
    turn = controller.run_turn(b"WAVDATA")
    assert turn.transcript == ""
    assert turn.reply == ""
    assert turn.reply_audio is None


def test_unavailable_raises(engine_thread):
    controller = VoiceController(None, engine_thread)
    assert not controller.available()
    with pytest.raises(RuntimeError):
        controller.run_turn(b"x")
    controller2 = VoiceController(FakeVoice(stt_ok=False), engine_thread)
    with pytest.raises(RuntimeError):
        controller2.run_turn(b"x")


def test_tts_failure_keeps_text_reply(engine_thread):
    class BrokenTTS(FakeVoice):
        async def synthesize(self, text, language=None):
            raise RuntimeError("tts down")

    controller = VoiceController(BrokenTTS(), engine_thread)
    turn = controller.run_turn(b"WAVDATA")
    assert turn.reply == "Certainly, Sir."
    assert turn.reply_audio is None
