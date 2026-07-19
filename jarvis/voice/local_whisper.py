"""
Local, offline speech-to-text using OpenAI's open-source Whisper.

Free and fully local — no API key, no cloud. Requires the ``openai-whisper``
package (https://github.com/openai/whisper), PyTorch and ffmpeg, and downloads
the model weights on first use. Heavier than the API, but nothing leaves the
machine — ideal for a desktop or self-hosted deployment.

(For low-power hardware like a Raspberry Pi, a lighter engine such as
``faster-whisper`` or ``whisper.cpp`` is usually a better fit; this backend
targets desktops.)
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from jarvis.voice.base import BaseSTT, Transcription, VoiceError


class LocalWhisperSTT(BaseSTT):
    """Speech-to-text via the local ``openai-whisper`` model."""

    name = "local"

    def __init__(self, model_size: str = "base") -> None:
        self.model_size = model_size
        self._model: object | None = None

    def _ensure_model(self) -> object:
        if self._model is None:
            try:
                import whisper
            except ImportError as exc:  # pragma: no cover - optional dependency
                raise VoiceError(
                    "Local Whisper needs the 'openai-whisper' package. "
                    "Install it with: pip install openai-whisper"
                ) from exc
            self._model = whisper.load_model(self.model_size)
        return self._model

    def _transcribe_sync(self, audio: bytes, suffix: str) -> Transcription:
        model = self._ensure_model()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio)
            path = tmp.name
        try:
            result = model.transcribe(path)  # type: ignore[attr-defined]
        finally:
            Path(path).unlink(missing_ok=True)
        return Transcription(
            text=str(result.get("text", "")).strip(),
            language=result.get("language"),
        )

    async def transcribe(self, audio: bytes, filename: str = "voice.ogg") -> Transcription:
        suffix = Path(filename).suffix or ".ogg"
        try:
            # Whisper transcription is CPU/GPU-bound — keep it off the event loop.
            return await asyncio.to_thread(self._transcribe_sync, audio, suffix)
        except VoiceError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise VoiceError(f"Local transcription failed: {exc}") from exc
