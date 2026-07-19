"""
Voice turn orchestration for the desktop app (GUI-free, fully testable).

A *voice turn* is: microphone audio → STT transcript → engine reply →
(optionally) TTS audio of the reply. The Qt layer only records/plays audio and
renders the results; everything else happens here on the engine thread's loop.
"""

from __future__ import annotations

from dataclasses import dataclass

from jarvis.voice import VoiceService


@dataclass
class VoiceTurn:
    """Result of one microphone interaction."""

    transcript: str
    reply: str
    reply_audio: bytes | None
    reply_audio_ext: str
    language: str | None = None


class VoiceController:
    """Runs voice turns against a :class:`VoiceService` and an engine.

    ``engine_thread`` is anything with ``submit(coro) -> Future`` and an
    ``engine`` attribute (the desktop app passes its
    :class:`~jarvis.desktop_app.engine_thread.EngineThread`).
    """

    def __init__(self, voice: VoiceService | None, engine_thread,
                *, speak_replies: bool = True) -> None:
        self._voice = voice
        self._engine_thread = engine_thread
        self.speak_replies = speak_replies

    def available(self) -> bool:
        return self._voice is not None and self._voice.stt_available()

    def can_speak(self) -> bool:
        return self._voice is not None and self._voice.tts_available()

    def run_turn(self, audio: bytes, *, filename: str = "voice.wav",
                session_id: str = "desktop", timeout: float = 300.0) -> VoiceTurn:
        """Blocking voice turn — call from a worker thread, not the GUI thread."""
        if not self.available():
            raise RuntimeError("Voice is not available (no STT backend).")

        async def _turn() -> VoiceTurn:
            transcription = await self._voice.transcribe(audio, filename=filename)
            text = (transcription.text or "").strip()
            if not text:
                return VoiceTurn(transcript="", reply="", reply_audio=None,
                                reply_audio_ext="")
            # Reply in whatever language the user spoke.
            engine = self._engine_thread.engine
            engine.session(session_id).scratch.pop("language", None)
            reply = await engine.ask(text, session_id=session_id)

            audio_out: bytes | None = None
            if self.speak_replies and self.can_speak():
                try:
                    audio_out = await self._voice.synthesize(
                        reply, transcription.language
                    )
                except Exception:  # noqa: BLE001 - the text reply still stands
                    audio_out = None
            return VoiceTurn(
                transcript=text,
                reply=reply,
                reply_audio=audio_out,
                reply_audio_ext=self._voice.tts_ext if audio_out else "",
                language=transcription.language,
            )

        return self._engine_thread.submit(_turn()).result(timeout)
