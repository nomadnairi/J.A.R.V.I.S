"""Desktop tools — expose desktop control to the LLM (security-gated)."""

from __future__ import annotations

from jarvis.desktop.controller import DesktopController
from jarvis.skills.base import BaseSkill, SkillResult
from jarvis.utils.exceptions import JarvisError


class _DesktopSkill(BaseSkill):
    priority = 20

    def __init__(self, controller: DesktopController) -> None:
        self.controller = controller

    def can_handle(self, text: str) -> bool:
        return False

    async def handle(self, text: str, context: dict | None = None) -> SkillResult:
        return SkillResult.not_handled()


class TypeTextSkill(_DesktopSkill):
    name = "desktop_type"
    description = "Type text on the keyboard (desktop control; off by default)."
    parameters = {
        "type": "object",
        "properties": {"text": {"type": "string", "description": "Text to type."}},
        "required": ["text"],
    }

    async def execute(self, text: str = "", **_: object) -> SkillResult:
        try:
            return SkillResult(text=await self.controller.type_text(text))
        except JarvisError as exc:
            return SkillResult(text=f"Cannot type: {exc}")


class PressKeySkill(_DesktopSkill):
    name = "desktop_press_key"
    description = "Press a key or hotkey combo (e.g. 'enter' or 'ctrl+c')."
    parameters = {
        "type": "object",
        "properties": {"key": {"type": "string", "description": "Key or combo."}},
        "required": ["key"],
    }

    async def execute(self, key: str = "", **_: object) -> SkillResult:
        try:
            return SkillResult(text=await self.controller.press_key(key))
        except JarvisError as exc:
            return SkillResult(text=f"Cannot press key: {exc}")


class OpenUrlSkill(_DesktopSkill):
    name = "open_url"
    description = "Open a URL in the default web browser."
    parameters = {
        "type": "object",
        "properties": {"url": {"type": "string", "description": "The URL to open."}},
        "required": ["url"],
    }

    async def execute(self, url: str = "", **_: object) -> SkillResult:
        try:
            return SkillResult(text=await self.controller.open_url(url))
        except JarvisError as exc:
            return SkillResult(text=f"Cannot open URL: {exc}")


class ScreenshotSkill(_DesktopSkill):
    name = "desktop_screenshot"
    description = "Take a screenshot of the screen and save it to a file."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Output path."}},
    }

    async def execute(self, path: str = "screenshot.png", **_: object) -> SkillResult:
        try:
            return SkillResult(text=await self.controller.screenshot(path or "screenshot.png"))
        except JarvisError as exc:
            return SkillResult(text=f"Cannot take screenshot: {exc}")


def desktop_skills(controller: DesktopController) -> list[BaseSkill]:
    return [
        TypeTextSkill(controller),
        PressKeySkill(controller),
        OpenUrlSkill(controller),
        ScreenshotSkill(controller),
    ]
