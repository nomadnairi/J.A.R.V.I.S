"""Tests for the update checker (offline, injected fetch)."""

from __future__ import annotations

from jarvis.core.updater import (
    UpdateInfo,
    check_github,
    is_newer,
    parse_version,
)


def test_parse_and_compare_versions():
    assert parse_version("v1.7.0") == (1, 7, 0)
    assert parse_version("1.7") == (1, 7, 0)
    assert parse_version("2.0.1-beta") == (2, 0, 1)
    assert is_newer("1.7.1", "1.7.0") is True
    assert is_newer("1.7.0", "1.7.0") is False
    assert is_newer("1.6.9", "1.7.0") is False


_RELEASES = [
    {"tag_name": "v1.7.0", "prerelease": True, "draft": False,
    "html_url": "https://gh/rel/1.7.0", "body": "notes",
    "assets": [{"name": "JARVIS-Setup.exe",
                "browser_download_url": "https://gh/dl/setup.exe"},
                {"name": "JARVIS-windows-amd64.exe",
                "browser_download_url": "https://gh/dl/portable.exe"}]},
    {"tag_name": "v1.6.0", "prerelease": False, "draft": False,
    "html_url": "https://gh/rel/1.6.0", "body": "", "assets": []},
]


def test_check_finds_newer_prerelease():
    info = check_github("1.6.5", include_prerelease=True,
                        fetch=lambda url: _RELEASES)
    assert info.available is True and info.latest == "v1.7.0"
    assert info.prerelease is True
    # Installer asset is preferred for the download link.
    assert info.download_url == "https://gh/dl/setup.exe"


def test_stable_channel_ignores_prerelease():
    info = check_github("1.5.0", include_prerelease=False,
                        fetch=lambda url: _RELEASES)
    assert info.latest == "v1.6.0" and info.available is True


def test_no_update_when_current_is_latest():
    info = check_github("1.7.0", include_prerelease=True,
                        fetch=lambda url: _RELEASES)
    assert info.available is False


def test_network_failure_is_soft():
    def boom(url):
        raise OSError("no network")
    info = check_github("1.7.0", fetch=boom)
    assert isinstance(info, UpdateInfo) and info.available is False
