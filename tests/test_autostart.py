"""Tests for the cross-platform autostart helper (filesystem, no OS hooks)."""

from __future__ import annotations

from jarvis.desktop_app import autostart


def test_enable_disable_linux(tmp_path):
    base = tmp_path / "autostart"
    assert not autostart.is_enabled(platform="linux", base=base)
    path = autostart.enable("/usr/bin/jarvis", platform="linux", base=base)
    assert path.exists() and path.suffix == ".desktop"
    body = path.read_text()
    assert "Exec=/usr/bin/jarvis" in body
    assert autostart.is_enabled(platform="linux", base=base)
    autostart.disable(platform="linux", base=base)
    assert not autostart.is_enabled(platform="linux", base=base)


def test_enable_windows(tmp_path):
    base = tmp_path / "startup"
    path = autostart.enable('"C:\\JARVIS.exe"', platform="win32", base=base)
    assert path.suffix == ".cmd"
    assert "JARVIS.exe" in path.read_text()


def test_enable_macos(tmp_path):
    base = tmp_path / "agents"
    path = autostart.enable("/Applications/JARVIS.app", platform="darwin",
                            base=base)
    assert path.suffix == ".plist"
    assert "RunAtLoad" in path.read_text()


def test_set_enabled_toggles(tmp_path):
    base = tmp_path / "a"
    autostart.set_enabled(True, "/bin/j", platform="linux", base=base)
    assert autostart.is_enabled(platform="linux", base=base)
    autostart.set_enabled(False, "/bin/j", platform="linux", base=base)
    assert not autostart.is_enabled(platform="linux", base=base)
    # Disabling again is a no-op, not an error.
    autostart.set_enabled(False, "/bin/j", platform="linux", base=base)


def test_config_behaviour_defaults(tmp_path):
    from jarvis.desktop_app.config import AppConfig

    cfg = AppConfig.load(tmp_path)
    assert cfg.minimize_to_tray is True
    assert cfg.start_on_boot is False
    assert cfg.notifications is True
    assert cfg.onboarded is False
    cfg.onboarded = True
    cfg.start_on_boot = True
    cfg.save(tmp_path)
    assert AppConfig.load(tmp_path).onboarded is True
    assert AppConfig.load(tmp_path).start_on_boot is True
