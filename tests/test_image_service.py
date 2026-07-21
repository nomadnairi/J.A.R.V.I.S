"""Tests for image generation (service plumbing + menu gating)."""

from __future__ import annotations

import base64

import pytest

from jarvis.config.settings import Settings
from jarvis.interfaces.bot_menu import screen_main
from jarvis.media import ImageService
from jarvis.media.image_service import ImageError


def _flat(rows):
    return [data for row in rows for _, data in row]


def test_available_requires_a_key():
    assert ImageService(api_key="").available() is False
    assert ImageService(api_key="sk-x").available() is True


def test_from_settings_falls_back_to_openai_creds():
    s = Settings(openai_api_key="sk-openai", log_file="", image_enabled=True)
    svc = ImageService.from_settings(s)
    assert svc.api_key == "sk-openai"
    # A dedicated image key wins when set.
    s2 = Settings(openai_api_key="sk-openai", image_api_key="sk-img", log_file="")
    assert ImageService.from_settings(s2).api_key == "sk-img"


@pytest.mark.asyncio
async def test_generate_decodes_b64(monkeypatch):
    raw = b"\x89PNG fake bytes"
    payload = base64.b64encode(raw).decode()

    class FakeImages:
        async def generate(self, **kwargs):
            assert kwargs["prompt"] == "a red cat"
            class R:
                data = [type("D", (), {"b64_json": payload})()]
            return R()

    class FakeClient:
        images = FakeImages()

    svc = ImageService(api_key="sk-x")
    monkeypatch.setattr(svc, "_ensure_client", lambda: FakeClient())
    out = await svc.generate("a red cat")
    assert out == raw


@pytest.mark.asyncio
async def test_generate_rejects_empty_prompt():
    with pytest.raises(ImageError):
        await ImageService(api_key="sk-x").generate("   ")


def test_main_menu_shows_image_button_when_enabled():
    _t, rows = screen_main("en", image_on=True)
    assert "m:image" in _flat(rows)
    _t2, rows2 = screen_main("en", image_on=False)
    assert "m:image" not in _flat(rows2)
