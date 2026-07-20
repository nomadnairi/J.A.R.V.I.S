"""
The PySide6 main window and login dialog.

Import-safe: PySide6 is imported inside :func:`run_app`, so the rest of the
package (config, API client, engine thread) works without Qt installed.
"""

from __future__ import annotations

from jarvis.desktop_app.api_client import ApiError, JarvisApiClient
from jarvis.desktop_app.config import AppConfig
from jarvis.desktop_app.strings import tr
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

_LANGS = [("en", "English"), ("ru", "Русский"), ("uz", "O'zbek")]


def run_app() -> int:
    """Create the Qt application and run the main loop."""
    try:
        from PySide6.QtCore import QObject, Signal
        from PySide6.QtWidgets import (
            QApplication,
            QCheckBox,
            QComboBox,
            QDialog,
            QFormLayout,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QMainWindow,
            QMessageBox,
            QPlainTextEdit,
            QPushButton,
            QRadioButton,
            QTabWidget,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "The desktop app needs PySide6. Install with: pip install PySide6"
        ) from exc

    config = AppConfig.load()

    class ReplyBridge(QObject):
        """Marshals engine-thread callbacks onto the GUI thread."""

        done = Signal(str, str)  # reply, error
        chunk = Signal(str)      # one streamed piece of the reply
        voice = Signal(str, str, str, str)  # transcript, reply, audio_path, error

    # -- login dialog ---------------------------------------------------------

    class LoginDialog(QDialog):
        def __init__(self) -> None:
            super().__init__()
            self.client: JarvisApiClient | None = None
            loc = config.language
            self.setWindowTitle(tr("login_title", loc))
            self.setMinimumWidth(460)

            outer = QVBoxLayout(self)
            outer.setContentsMargins(28, 28, 28, 28)

            card = QWidget()
            card.setObjectName("Card")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(28, 26, 28, 26)
            layout.setSpacing(12)
            outer.addWidget(card)

            wordmark = QLabel("J.A.R.V.I.S.")
            wordmark.setObjectName("Wordmark")
            title = QLabel(tr("login_title", loc))
            title.setObjectName("Title")
            layout.addWidget(wordmark)
            layout.addWidget(title)
            layout.addSpacing(6)

            self.local_radio = QRadioButton(tr("mode_local", loc))
            self.remote_radio = QRadioButton(tr("mode_remote", loc))
            (self.remote_radio if config.mode == "remote"
             else self.local_radio).setChecked(True)
            layout.addWidget(self.local_radio)
            local_hint = QLabel(tr("login_local_hint", loc))
            local_hint.setObjectName("Hint")
            local_hint.setWordWrap(True)
            layout.addWidget(local_hint)
            layout.addWidget(self.remote_radio)
            remote_hint = QLabel(tr("login_remote_hint", loc))
            remote_hint.setObjectName("Hint")
            remote_hint.setWordWrap(True)
            layout.addWidget(remote_hint)

            form = QFormLayout()
            form.setSpacing(10)
            self.server = QLineEdit(config.server_url or "http://localhost:8000")
            self.user = QLineEdit(config.username)
            self.password = QLineEdit()
            self.password.setEchoMode(QLineEdit.EchoMode.Password)
            for field in (self.server, self.user, self.password):
                field.setMinimumHeight(40)
            form.addRow(tr("server_url", loc), self.server)
            form.addRow(tr("username", loc), self.user)
            form.addRow(tr("password", loc), self.password)
            layout.addSpacing(6)
            layout.addLayout(form)
            layout.addSpacing(8)

            buttons = QHBoxLayout()
            buttons.setSpacing(10)
            sign_in = QPushButton(tr("sign_in", loc))
            sign_in.setObjectName("Primary")
            sign_in.setMinimumHeight(44)
            local = QPushButton(tr("continue_local", loc))
            local.setMinimumHeight(44)
            sign_in.clicked.connect(self._sign_in)
            local.clicked.connect(self._local)
            buttons.addWidget(sign_in, stretch=1)
            buttons.addWidget(local, stretch=1)
            layout.addLayout(buttons)

        def _local(self) -> None:
            config.mode = "local"
            config.save()
            self.accept()

        def _sign_in(self) -> None:
            loc = config.language
            client = JarvisApiClient(self.server.text().strip())
            try:
                client.login(self.user.text().strip(), self.password.text())
            except ApiError as exc:
                QMessageBox.warning(self, tr("login_title", loc),
                                    tr("login_failed", loc, error=exc.detail))
                return
            config.mode = "remote"
            config.server_url = client.base_url
            config.username = self.user.text().strip()
            config.auth_token = client.token
            config.save()
            self.client = client
            self.accept()

    # -- main window ------------------------------------------------------

    class MainWindow(QMainWindow):
        def __init__(self, client: JarvisApiClient | None) -> None:
            super().__init__()
            self.client = client
            self.engine_thread = None
            self.bridge = ReplyBridge()
            self.bridge.done.connect(self._on_reply)
            self.bridge.chunk.connect(self._on_chunk)
            self._streaming = False
            loc = config.language

            self.setWindowTitle(tr("app_title", loc))
            self.resize(1040, 720)
            self.setMinimumSize(880, 600)

            tabs = QTabWidget()
            tabs.addTab(self._chat_tab(), tr("tab_chat", loc))
            tabs.addTab(self._voice_tab(), tr("tab_voice", loc))
            tabs.addTab(self._assistant_tab(), tr("tab_assistant", loc))
            tabs.addTab(self._capabilities_tab(), tr("tab_capabilities", loc))
            tabs.addTab(self._integrations_tab(), tr("tab_integrations", loc))
            tabs.addTab(self._memory_tab(), tr("tab_memory", loc))
            tabs.addTab(self._logs_tab(), tr("tab_logs", loc))

            container = QWidget()
            root = QVBoxLayout(container)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(0)
            root.addWidget(self._header())
            body = QWidget()
            body_layout = QVBoxLayout(body)
            body_layout.setContentsMargins(18, 8, 18, 18)
            body_layout.addWidget(tabs)
            root.addWidget(body, stretch=1)
            self.setCentralWidget(container)

            self.voice_controller = None
            if config.mode == "local":
                self._start_local_engine()
                self._init_voice()

        def _header(self) -> "QWidget":
            bar = QWidget()
            bar.setObjectName("Header")
            bar.setFixedHeight(64)
            row = QHBoxLayout(bar)
            row.setContentsMargins(20, 0, 20, 0)

            wordmark = QLabel("J.A.R.V.I.S.")
            wordmark.setObjectName("Wordmark")
            row.addWidget(wordmark)

            mode_text = ("● local" if config.mode == "local"
                        else f"● {config.username or 'account'}")
            mode = QLabel(mode_text)
            mode.setObjectName("Subtle")
            row.addSpacing(14)
            row.addWidget(mode)

            row.addStretch(1)
            status = QLabel("● online")
            status.setObjectName("StatusDot")
            row.addWidget(status)
            return bar

        # -- engine -----------------------------------------------------------

        def _start_local_engine(self) -> None:
            from jarvis.config.settings import Settings
            from jarvis.desktop_app.engine_thread import EngineThread

            overrides = config.to_settings_overrides()
            settings = Settings(**overrides)
            self.engine_thread = EngineThread(settings)
            try:
                self.engine_thread.start()
            except Exception as exc:  # noqa: BLE001 - shown in the chat view
                self._append_system(tr("error", config.language, error=exc))

        def _init_voice(self) -> None:
            if self.engine_thread is None or not config.voice_enabled:
                return
            try:
                from jarvis.config.settings import Settings
                from jarvis.desktop_app.voice_controller import VoiceController
                from jarvis.voice import VoiceService

                settings = Settings(**config.to_settings_overrides())
                voice = VoiceService.from_settings(settings)
                self.voice_controller = VoiceController(
                    voice, self.engine_thread
                )
                self._update_voice_ui()
            except Exception as exc:  # noqa: BLE001 - voice is optional
                logger.warning("Voice init failed: %s", exc)

        # -- chat tab -----------------------------------------------------

        def _chat_tab(self) -> "QWidget":
            loc = config.language
            widget = QWidget()
            layout = QVBoxLayout(widget)

            top = QHBoxLayout()
            top.addWidget(QLabel(tr("language", loc)))
            self.lang_box = QComboBox()
            for code, label in _LANGS:
                self.lang_box.addItem(label, code)
                if code == loc:
                    self.lang_box.setCurrentIndex(self.lang_box.count() - 1)
            self.lang_box.currentIndexChanged.connect(self._change_language)
            top.addWidget(self.lang_box)
            top.addStretch(1)
            layout.addLayout(top)

            self.transcript = QTextEdit()
            self.transcript.setReadOnly(True)
            self.transcript.setFrameStyle(0)
            layout.addWidget(self.transcript, stretch=1)
            self._messages: list[tuple[str, str]] = []
            self._pending = False

            row = QHBoxLayout()
            row.setSpacing(10)
            self.input = QLineEdit()
            self.input.setPlaceholderText("Message J.A.R.V.I.S. …")
            self.input.setMinimumHeight(44)
            self.input.returnPressed.connect(self._send)
            send = QPushButton(tr("send", loc))
            send.setObjectName("Primary")
            send.setMinimumHeight(44)
            send.clicked.connect(self._send)
            row.addWidget(self.input, stretch=1)
            row.addWidget(send)
            layout.addLayout(row)
            return widget

        def _render_chat(self) -> None:
            from jarvis.desktop_app.theme import bubble_html
            html = "".join(bubble_html(r, t) for r, t in self._messages)
            if self._pending:
                html += bubble_html("system", tr("thinking", config.language))
            self.transcript.setHtml(html)
            bar = self.transcript.verticalScrollBar()
            bar.setValue(bar.maximum())

        def _append_system(self, text: str) -> None:
            self._messages.append(("system", text))
            self._render_chat()

        def _change_language(self) -> None:
            config.language = self.lang_box.currentData()
            config.save()
            if self.engine_thread is not None:
                session = self.engine_thread.engine.session("desktop")
                session.scratch["language"] = config.language

        def _send(self) -> None:
            text = self.input.text().strip()
            if not text:
                return
            loc = config.language
            self.input.clear()
            self._messages.append(("user", text))
            self._pending = True
            self._render_chat()

            self._streaming = False
            if config.mode == "remote" and self.client is not None:
                import threading

                def _worker() -> None:
                    try:
                        self.client.chat_stream(
                            text, on_chunk=self.bridge.chunk.emit
                        )
                        self.bridge.done.emit("", "")
                    except ApiError as exc:
                        self.bridge.done.emit("", exc.detail)

                threading.Thread(target=_worker, daemon=True).start()
            elif self.engine_thread is not None:
                session = self.engine_thread.engine.session("desktop")
                session.scratch["language"] = config.language
                self.engine_thread.stream_async(
                    text,
                    on_chunk=self.bridge.chunk.emit,
                    on_done=lambda err: self.bridge.done.emit(
                        "", str(err) if err else ""
                    ),
                )
            else:
                self.bridge.done.emit("", tr("not_signed_in", loc))

        def _on_chunk(self, text: str) -> None:
            if not self._streaming:
                self._streaming = True
                self._pending = False
                self._messages.append(("assistant", ""))
            role, prev = self._messages[-1]
            self._messages[-1] = ("assistant", prev + text)
            self._render_chat()

        def _on_reply(self, reply: str, error: str) -> None:
            loc = config.language
            self._pending = False
            was_streaming = self._streaming
            self._streaming = False
            if error:
                self._append_system(tr("error", loc, error=error))
            elif reply and not was_streaming:
                self._messages.append(("assistant", reply))
                self._render_chat()

        # -- voice tab -----------------------------------------------------

        def _voice_tab(self) -> "QWidget":
            loc = config.language
            widget = QWidget()
            layout = QVBoxLayout(widget)

            self.voice_status = QLabel(tr("voice_unavailable_desktop", loc))
            self.voice_status.setWordWrap(True)
            layout.addWidget(self.voice_status)

            self.voice_button = QPushButton(tr("voice_record", loc))
            self.voice_button.setObjectName("Record")
            self.voice_button.setEnabled(False)
            self.voice_button.setMinimumHeight(64)
            self.voice_button.clicked.connect(self._toggle_recording)
            layout.addWidget(self.voice_button)

            self.voice_speak = QCheckBox(tr("voice_speak_replies", loc))
            self.voice_speak.setChecked(True)
            layout.addWidget(self.voice_speak)

            self.voice_output = QTextEdit()
            self.voice_output.setReadOnly(True)
            layout.addWidget(self.voice_output, stretch=1)

            self._recording = False
            self._recorder = None
            self._capture = None
            self._audio_in = None
            self._player = None
            self._audio_out = None
            self._voice_file = ""
            self.bridge.voice.connect(self._on_voice_result)
            return widget

        def _update_voice_ui(self) -> None:
            loc = config.language
            if self.voice_controller is not None and self.voice_controller.available():
                self.voice_status.setText("")
                self.voice_button.setEnabled(True)
            else:
                self.voice_status.setText(tr("voice_unavailable_desktop", loc))
                self.voice_button.setEnabled(False)

        def _toggle_recording(self) -> None:
            loc = config.language
            if self._recording:
                self._recording = False
                self.voice_button.setText(tr("voice_record", loc))
                if self._recorder is not None:
                    self._recorder.stop()
                return

            try:
                import tempfile

                from PySide6.QtCore import QUrl
                from PySide6.QtMultimedia import (
                    QAudioInput,
                    QMediaCaptureSession,
                    QMediaFormat,
                    QMediaRecorder,
                )
            except ImportError as exc:
                self.voice_status.setText(tr("error", loc, error=exc))
                return

            self._voice_file = tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False
            ).name
            self._capture = QMediaCaptureSession()
            self._audio_in = QAudioInput()
            self._capture.setAudioInput(self._audio_in)
            self._recorder = QMediaRecorder()
            self._capture.setRecorder(self._recorder)
            fmt = QMediaFormat()
            fmt.setFileFormat(QMediaFormat.FileFormat.Wave)
            self._recorder.setMediaFormat(fmt)
            self._recorder.setOutputLocation(QUrl.fromLocalFile(self._voice_file))
            self._recorder.recorderStateChanged.connect(self._on_recorder_state)
            self._recording = True
            self.voice_button.setText(tr("voice_stop", loc))
            self._recorder.record()

        def _on_recorder_state(self, state) -> None:
            from PySide6.QtMultimedia import QMediaRecorder

            if state != QMediaRecorder.RecorderState.StoppedState:
                return
            loc = config.language
            self.voice_status.setText(tr("voice_processing", loc))

            import threading
            from pathlib import Path

            path = self._voice_file
            speak = self.voice_speak.isChecked()

            def _worker() -> None:
                try:
                    audio = Path(path).read_bytes()
                    controller = self.voice_controller
                    controller.speak_replies = speak
                    turn = controller.run_turn(audio, filename="voice.wav")
                    out_path = ""
                    if turn.reply_audio:
                        import tempfile
                        out = tempfile.NamedTemporaryFile(
                            suffix=f".{turn.reply_audio_ext}", delete=False
                        )
                        out.write(turn.reply_audio)
                        out.close()
                        out_path = out.name
                    self.bridge.voice.emit(turn.transcript, turn.reply,
                                        out_path, "")
                except Exception as exc:  # noqa: BLE001 - shown in the UI
                    self.bridge.voice.emit("", "", "", str(exc))
                finally:
                    Path(path).unlink(missing_ok=True)

            threading.Thread(target=_worker, daemon=True).start()

        def _on_voice_result(self, transcript: str, reply: str,
                            audio_path: str, error: str) -> None:
            loc = config.language
            self.voice_status.setText("")
            if error:
                self.voice_output.append(f"<i>{tr('error', loc, error=error)}</i>")
                return
            if not transcript:
                self.voice_output.append(
                    f"<i>{tr('voice_no_speech', loc)}</i>")
                return
            self.voice_output.append(
                f"<b>{tr('voice_you_said', loc)}:</b> {transcript}")
            self.voice_output.append(f"<b>J.A.R.V.I.S.:</b> {reply}")
            # Mirror the exchange into the chat transcript.
            self._messages.append(("user", f"🎙 {transcript}"))
            self._messages.append(("assistant", reply))
            self._render_chat()
            if audio_path:
                self._play_audio(audio_path)

        def _play_audio(self, path: str) -> None:
            try:
                from PySide6.QtCore import QUrl
                from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
            except ImportError:
                return
            self._player = QMediaPlayer()
            self._audio_out = QAudioOutput()
            self._player.setAudioOutput(self._audio_out)
            self._player.setSource(QUrl.fromLocalFile(path))
            self._player.play()

        # -- assistant tab ------------------------------------------------

        def _assistant_tab(self) -> "QWidget":
            loc = config.language
            widget = QWidget()
            form = QFormLayout(widget)

            self.provider_box = QComboBox()
            self.provider_box.addItems(["anthropic", "openai"])
            self.provider_box.setCurrentText(config.llm_provider)
            self.model_edit = QLineEdit(config.llm_model)
            self.anthropic_edit = QLineEdit(config.anthropic_api_key)
            self.anthropic_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.openai_edit = QLineEdit(config.openai_api_key)
            self.openai_edit.setEchoMode(QLineEdit.EchoMode.Password)

            form.addRow(tr("provider", loc), self.provider_box)
            form.addRow(tr("model", loc), self.model_edit)
            form.addRow(tr("anthropic_key", loc), self.anthropic_edit)
            form.addRow(tr("openai_key", loc), self.openai_edit)

            save = QPushButton(tr("save", loc))
            save.setObjectName("Primary")
            save.setMinimumHeight(40)
            save.clicked.connect(self._save_assistant)
            form.addRow(save)
            return widget

        def _save_assistant(self) -> None:
            config.llm_provider = self.provider_box.currentText()
            config.llm_model = self.model_edit.text().strip()
            config.anthropic_api_key = self.anthropic_edit.text().strip()
            config.openai_api_key = self.openai_edit.text().strip()
            config.save()
            QMessageBox.information(self, "J.A.R.V.I.S.",
                                    tr("saved", config.language))

        # -- capabilities tab (granular PC access) --------------------------

        def _capabilities_tab(self) -> "QWidget":
            loc = config.language
            widget = QWidget()
            layout = QVBoxLayout(widget)
            intro = QLabel(tr("cap_intro", loc))
            intro.setWordWrap(True)
            layout.addWidget(intro)

            self.cap_read = QCheckBox(tr("cap_file_read", loc))
            self.cap_read.setChecked(config.allow_file_read)
            self.cap_write = QCheckBox(tr("cap_file_write", loc))
            self.cap_write.setChecked(config.allow_file_write)
            self.cap_shell = QCheckBox(tr("cap_shell", loc))
            self.cap_shell.setChecked(config.allow_shell)
            self.cap_desktop = QCheckBox(tr("cap_desktop", loc))
            self.cap_desktop.setChecked(config.allow_desktop_control)
            for box in (self.cap_read, self.cap_write, self.cap_shell,
                        self.cap_desktop):
                layout.addWidget(box)

            form = QFormLayout()
            self.workspace_edit = QLineEdit(config.workspace_root)
            form.addRow(tr("workspace", loc), self.workspace_edit)
            layout.addLayout(form)

            save = QPushButton(tr("save", loc))
            save.setObjectName("Primary")
            save.setMinimumHeight(40)
            save.clicked.connect(self._save_capabilities)
            layout.addWidget(save)
            layout.addStretch(1)
            return widget

        def _save_capabilities(self) -> None:
            config.allow_file_read = self.cap_read.isChecked()
            config.allow_file_write = self.cap_write.isChecked()
            config.allow_shell = self.cap_shell.isChecked()
            config.allow_desktop_control = self.cap_desktop.isChecked()
            config.workspace_root = self.workspace_edit.text().strip()
            config.save()
            QMessageBox.information(self, "J.A.R.V.I.S.",
                                    tr("saved", config.language))

        # -- integrations tab ---------------------------------------------

        def _integrations_tab(self) -> "QWidget":
            loc = config.language
            widget = QWidget()
            layout = QVBoxLayout(widget)

            self.int_weather = QCheckBox(tr("int_weather", loc))
            self.int_weather.setChecked(config.weather_enabled)
            layout.addWidget(self.int_weather)

            form = QFormLayout()
            self.ha_url = QLineEdit(config.homeassistant_url)
            self.ha_token = QLineEdit(config.homeassistant_token)
            self.ha_token.setEchoMode(QLineEdit.EchoMode.Password)
            self.tg_token = QLineEdit(config.telegram_bot_token)
            self.tg_token.setEchoMode(QLineEdit.EchoMode.Password)
            self.tg_channel = QLineEdit(config.telegram_channel)
            form.addRow(tr("int_ha_url", loc), self.ha_url)
            form.addRow(tr("int_ha_token", loc), self.ha_token)
            form.addRow(tr("int_tg_token", loc), self.tg_token)
            form.addRow(tr("int_tg_channel", loc), self.tg_channel)
            layout.addLayout(form)

            self.tg_send = QCheckBox(tr("int_tg_send", loc))
            self.tg_send.setChecked(config.telegram_send_enabled)
            layout.addWidget(self.tg_send)

            save = QPushButton(tr("save", loc))
            save.setObjectName("Primary")
            save.setMinimumHeight(40)
            save.clicked.connect(self._save_integrations)
            layout.addWidget(save)
            layout.addStretch(1)
            return widget

        def _save_integrations(self) -> None:
            config.weather_enabled = self.int_weather.isChecked()
            config.homeassistant_url = self.ha_url.text().strip()
            config.homeassistant_token = self.ha_token.text().strip()
            config.telegram_bot_token = self.tg_token.text().strip()
            config.telegram_channel = self.tg_channel.text().strip()
            config.telegram_send_enabled = self.tg_send.isChecked()
            config.save()
            QMessageBox.information(self, "J.A.R.V.I.S.",
                                    tr("saved", config.language))

        # -- memory tab -----------------------------------------------------

        def _memory_tab(self) -> "QWidget":
            loc = config.language
            widget = QWidget()
            layout = QVBoxLayout(widget)

            reset = QPushButton(tr("mem_reset", loc))
            forget = QPushButton(tr("mem_forget", loc))
            reset.clicked.connect(lambda: self._memory_action("reset"))
            forget.clicked.connect(lambda: self._memory_action("forget"))
            layout.addWidget(reset)
            layout.addWidget(forget)

            link = QPushButton(tr("link_telegram", loc))
            link.clicked.connect(self._link_telegram)
            layout.addWidget(link)

            self.memory_status = QLabel("")
            layout.addWidget(self.memory_status)
            layout.addStretch(1)
            return widget

        def _memory_action(self, action: str) -> None:
            loc = config.language
            try:
                if self.engine_thread is not None:
                    getattr(self.engine_thread, action)()
                self.memory_status.setText(tr("mem_done", loc))
            except Exception as exc:  # noqa: BLE001 - shown in the UI
                self.memory_status.setText(tr("error", loc, error=exc))

        def _link_telegram(self) -> None:
            loc = config.language
            if self.client is None:
                self.memory_status.setText(tr("not_signed_in", loc))
                return
            try:
                code = self.client.pairing_code()
            except ApiError as exc:
                self.memory_status.setText(tr("error", loc, error=exc.detail))
                return
            self.memory_status.setText(tr("link_code_info", loc, code=code))

        # -- logs tab ---------------------------------------------------------

        def _logs_tab(self) -> "QWidget":
            widget = QWidget()
            layout = QVBoxLayout(widget)
            self.log_view = QPlainTextEdit()
            self.log_view.setReadOnly(True)
            layout.addWidget(self.log_view)

            refresh = QPushButton("⟳")
            refresh.clicked.connect(self._refresh_logs)
            layout.addWidget(refresh)
            self._refresh_logs()
            return widget

        def _refresh_logs(self) -> None:
            from pathlib import Path
            for candidate in ("logs/jarvis.log", "logs/audit.log"):
                path = Path(candidate)
                if path.exists():
                    lines = path.read_text(encoding="utf-8",
                                        errors="replace").splitlines()[-500:]
                    self.log_view.setPlainText("\n".join(lines))
                    return
            self.log_view.setPlainText("(no logs yet)")

        # -- shutdown -------------------------------------------------------

        def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
            if self.engine_thread is not None:
                self.engine_thread.stop()
            event.accept()

    from PySide6.QtGui import QFont

    from jarvis.desktop_app.theme import stylesheet

    app = QApplication([])
    app.setApplicationName("JARVIS")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(stylesheet())

    client: JarvisApiClient | None = None
    if config.mode == "remote" and config.auth_token and config.server_url:
        # Try the saved token first; fall back to the login dialog.
        candidate = JarvisApiClient(config.server_url, token=config.auth_token)
        try:
            candidate.me()
            client = candidate
        except ApiError:
            config.auth_token = ""
            config.save()

    if client is None:
        dialog = LoginDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return 0
        client = dialog.client

    window = MainWindow(client)
    window.show()
    return app.exec()
