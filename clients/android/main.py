"""
J.A.R.V.I.S. for Android — a thin Kivy client for the HTTP API.

The phone is a remote control: the heavy engine runs on your server (or PC),
this app signs in with the username/password issued after purchase and chats
over the same API the desktop app uses. Memory is shared server-side, so the
assistant remembers you across the Telegram bot, desktop and phone.

Build with buildozer (see clients/android/README.md).
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from kivy.app import App
from kivy.clock import mainthread
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.textinput import TextInput

from jarvis_client import ApiError, JarvisApiClient

CONFIG_FILE = "jarvis_mobile.json"


def _config_path(app: App) -> Path:
    return Path(app.user_data_dir) / CONFIG_FILE


def load_config(app: App) -> dict:
    try:
        return json.loads(_config_path(app).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(app: App, data: dict) -> None:
    path = _config_path(app)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="login", **kwargs)
        layout = BoxLayout(orientation="vertical", padding=24, spacing=12)
        layout.add_widget(Label(text="J.A.R.V.I.S.", font_size="28sp",
                                size_hint_y=None, height=64))
        self.server = TextInput(hint_text="Server URL (https://…)",
                                multiline=False, size_hint_y=None, height=48)
        self.username = TextInput(hint_text="Username", multiline=False,
                                size_hint_y=None, height=48)
        self.password = TextInput(hint_text="Password", password=True,
                                multiline=False, size_hint_y=None, height=48)
        self.status = Label(text="", size_hint_y=None, height=32)
        button = Button(text="Sign in", size_hint_y=None, height=56)
        button.bind(on_release=self._sign_in)
        for widget in (self.server, self.username, self.password, button,
                    self.status):
            layout.add_widget(widget)
        layout.add_widget(Label())  # spacer
        self.add_widget(layout)

    def on_pre_enter(self):
        app = App.get_running_app()
        config = load_config(app)
        self.server.text = config.get("server_url", "")
        self.username.text = config.get("username", "")

    def _sign_in(self, *_args):
        server = self.server.text.strip()
        user = self.username.text.strip()
        password = self.password.text
        if not server or not user:
            self.status.text = "Fill in server, username and password."
            return
        self.status.text = "Signing in…"

        def worker():
            client = JarvisApiClient(server)
            try:
                client.login(user, password)
            except ApiError as exc:
                self._fail(exc.detail or "Sign-in failed")
                return
            self._success(client)

        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def _fail(self, message: str):
        self.status.text = message

    @mainthread
    def _success(self, client: JarvisApiClient):
        app = App.get_running_app()
        app.client = client
        save_config(app, {
            "server_url": client.base_url,
            "username": self.username.text.strip(),
            "token": client.token,
        })
        app.root.current = "chat"


class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="chat", **kwargs)
        layout = BoxLayout(orientation="vertical", padding=12, spacing=8)

        self.transcript = Label(text="", markup=True, halign="left",
                                valign="top", size_hint_y=None)
        self.transcript.bind(
            width=lambda w, val: setattr(w, "text_size", (val, None)),
            texture_size=lambda w, val: setattr(w, "height", val[1]),
        )
        scroll = ScrollView()
        scroll.add_widget(self.transcript)
        layout.add_widget(scroll)

        row = BoxLayout(size_hint_y=None, height=56, spacing=8)
        self.input = TextInput(hint_text="Message…", multiline=False)
        self.input.bind(on_text_validate=self._send)
        send = Button(text="➤", size_hint_x=None, width=64)
        send.bind(on_release=self._send)
        row.add_widget(self.input)
        row.add_widget(send)
        layout.add_widget(row)
        self.add_widget(layout)

    def _append(self, line: str):
        self.transcript.text += line + "\n\n"

    def _send(self, *_args):
        app = App.get_running_app()
        text = self.input.text.strip()
        if not text or app.client is None:
            return
        self.input.text = ""
        self._append(f"[b]You:[/b] {text}")
        self._streaming = False

        def worker():
            try:
                app.client.chat_stream(text, on_chunk=self._chunk)
                self._finish()
            except ApiError as exc:
                self._receive(f"[i]Error: {exc.detail}[/i]")

        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def _chunk(self, piece: str):
        if not self._streaming:
            self._streaming = True
            self.transcript.text += "[b]J.A.R.V.I.S.:[/b] "
        self.transcript.text += piece

    @mainthread
    def _finish(self):
        self.transcript.text += "\n\n"
        self._streaming = False

    @mainthread
    def _receive(self, line: str):
        self._append(line)


class JarvisMobileApp(App):
    title = "J.A.R.V.I.S."

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client: JarvisApiClient | None = None

    def build(self):
        Window.softinput_mode = "below_target"
        manager = ScreenManager()
        manager.add_widget(LoginScreen())
        manager.add_widget(ChatScreen())

        # Try the saved token so the user stays signed in.
        config = load_config(self)
        if config.get("token") and config.get("server_url"):
            candidate = JarvisApiClient(config["server_url"],
                                        token=config["token"])
            def check():
                try:
                    candidate.me()
                except ApiError:
                    return
                self.client = candidate
                self._go_chat(manager)
            threading.Thread(target=check, daemon=True).start()
        return manager

    @mainthread
    def _go_chat(self, manager: ScreenManager):
        manager.current = "chat"


if __name__ == "__main__":
    JarvisMobileApp().run()
