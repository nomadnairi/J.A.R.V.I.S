"""Tests for multi-provider model profiles and runtime switching."""

from __future__ import annotations


from jarvis.config.settings import Settings
from jarvis.llm.base import LLMProvider, LLMResult
from jarvis.llm.client import LLMClient


class StubProvider(LLMProvider):
    name = "stub"

    def __init__(self, label: str):
        super().__init__(api_key="k", model=f"{label}-model")
        self.label = label

    def is_available(self) -> bool:
        return True

    async def complete(self, messages, system=None, tools=None, model=None):
        return LLMResult(text=f"reply from {self.label}", model=self.model,
                        provider=self.label)

    async def stream(self, messages, system=None, model=None):
        yield f"[{self.label}] "
        yield "hello"

    def continuation_messages(self, result, tool_results):
        return []


# -- profile building from settings ------------------------------------------


def test_profiles_built_from_available_keys():
    settings = Settings(
        anthropic_api_key="a", openai_api_key="o", openrouter_api_key="r",
        log_file="",
    )
    client = LLMClient.from_settings(settings)
    assert set(client.list_profiles()) == {"claude", "gpt", "openrouter"}
    assert client.profiles["openrouter"].base_url == "https://openrouter.ai/api/v1"
    assert client.profiles["gpt"].base_url == ""  # official OpenAI


def test_only_configured_providers_appear():
    settings = Settings(anthropic_api_key="a", openai_api_key="",
                        openrouter_api_key="", log_file="")
    client = LLMClient.from_settings(settings)
    assert client.list_profiles() == ["claude"]


# -- selection ----------------------------------------------------------------


async def test_complete_uses_selected_profile():
    client = LLMClient(
        primary=StubProvider("primary"),
        profiles={"claude": StubProvider("claude"), "gpt": StubProvider("gpt")},
    )
    out = await client.complete([{"role": "user", "content": "hi"}],
                                profile="gpt")
    assert out.text == "reply from gpt"
    # Unknown / no profile falls back to the primary chain.
    out = await client.complete([{"role": "user", "content": "hi"}],
                                profile="nope")
    assert out.text == "reply from primary"
    out = await client.complete([{"role": "user", "content": "hi"}])
    assert out.text == "reply from primary"


async def test_stream_uses_selected_profile():
    client = LLMClient(
        primary=StubProvider("primary"),
        profiles={"claude": StubProvider("claude")},
    )
    chunks = [c async for c in client.stream([{"role": "user", "content": "x"}],
                                            profile="claude")]
    assert "".join(chunks) == "[claude] hello"


# -- user preferences persistence --------------------------------------------


def test_user_prefs_model_roundtrip(tmp_path):
    from jarvis.interfaces.user_prefs import UserPreferences

    prefs = UserPreferences(str(tmp_path / "p.db"))
    assert prefs.get_model(1) is None
    prefs.set_model(1, "gpt")
    assert prefs.get_model(1) == "gpt"
    prefs.set_model(1, "")  # "auto" clears it
    assert prefs.get_model(1) is None
    # Language and model are independent.
    prefs.set_language(1, "ru")
    prefs.set_model(1, "claude")
    assert prefs.get_language(1) == "ru"
    assert prefs.get_model(1) == "claude"
    prefs.close()


def test_user_prefs_migrates_old_schema(tmp_path):
    import sqlite3

    db = tmp_path / "old.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE user_prefs (user_id TEXT PRIMARY KEY, language TEXT)")
    conn.execute("INSERT INTO user_prefs VALUES ('5', 'ru')")
    conn.commit()
    conn.close()

    from jarvis.interfaces.user_prefs import UserPreferences

    prefs = UserPreferences(str(db))
    assert prefs.get_language(5) == "ru"
    assert prefs.get_model(5) is None
    prefs.set_model(5, "openrouter")
    assert prefs.get_model(5) == "openrouter"
    prefs.close()
