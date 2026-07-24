"""
Update checker.

Compares the running version against the latest GitHub release (or a channel)
and reports whether an update is available, with a download URL. Network access
is injectable so the logic is fully unit-testable offline.

Actually *applying* an update is client-specific (the desktop app downloads and
launches the Windows installer); this module only decides *whether* and *where*.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

#: Default source repository for releases.
DEFAULT_REPO = "nomadnairi/J.A.R.V.I.S"


def parse_version(text: str) -> tuple[int, ...]:
    """Turn ``"v1.7.0"`` / ``"1.7"`` into a comparable tuple ``(1, 7, 0)``."""
    text = (text or "").strip().lstrip("vV").split("-")[0].split("+")[0]
    parts: list[int] = []
    for chunk in text.split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def is_newer(candidate: str, current: str) -> bool:
    """True if ``candidate`` is a strictly newer version than ``current``."""
    return parse_version(candidate) > parse_version(current)


@dataclass(frozen=True)
class UpdateInfo:
    """Result of an update check."""

    current: str
    latest: str
    available: bool
    url: str = ""
    download_url: str = ""
    notes: str = ""
    channel: str = "github"
    prerelease: bool = False

    def as_dict(self) -> dict:
        return {
            "current": self.current, "latest": self.latest,
            "available": self.available, "url": self.url,
            "download_url": self.download_url, "notes": self.notes[:2000],
            "channel": self.channel, "prerelease": self.prerelease,
        }


def _http_json(url: str, timeout: int = 10):
    if not url.startswith("https://"):  # defensive
        raise ValueError("Refusing non-https update request.")
    req = urllib.request.Request(url, headers={
        "User-Agent": "jarvis-updater", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310  # nosec B310
        return json.loads(resp.read().decode("utf-8"))


def download(url: str, dest: str, *, opener=None, chunk: int = 65536,
            on_progress=None) -> str:
    """Stream ``url`` to ``dest`` (installer download). Returns ``dest``.

    ``on_progress(done, total)`` is called as bytes arrive (total may be 0 if
    the server doesn't report a length). ``opener`` is injectable for testing.
    """
    if not url.startswith("https://"):
        raise ValueError("Refusing non-https download.")
    opener = opener or urllib.request.build_opener()
    req = urllib.request.Request(url, headers={"User-Agent": "jarvis-updater"})
    with opener.open(req) as resp:  # noqa: S310  # nosec B310
        total = int((resp.headers.get("Content-Length") if resp.headers else 0) or 0)
        done = 0
        with open(dest, "wb") as fh:
            while True:
                block = resp.read(chunk)
                if not block:
                    break
                fh.write(block)
                done += len(block)
                if on_progress:
                    on_progress(done, total)
    return dest


def _pick_asset(assets: list[dict], prefer: str = ".exe") -> str:
    """Prefer an installer, then any matching-suffix asset, else the first."""
    for a in assets:
        if "setup" in a.get("name", "").lower() and a.get("name", "").endswith(prefer):
            return a.get("browser_download_url", "")
    for a in assets:
        if a.get("name", "").endswith(prefer):
            return a.get("browser_download_url", "")
    return assets[0].get("browser_download_url", "") if assets else ""


def check_github(current: str, *, repo: str = DEFAULT_REPO,
                include_prerelease: bool = True,
                asset_suffix: str = ".exe",
                fetch=_http_json) -> UpdateInfo:
    """Check the newest GitHub release for ``repo`` against ``current``.

    ``include_prerelease`` picks the newest release including pre-releases
    (the "early/grey" channel); otherwise only stable releases are considered.
    ``fetch`` is injectable for testing.
    """
    try:
        releases = fetch(f"https://api.github.com/repos/{repo}/releases?per_page=15")
    except Exception as exc:  # noqa: BLE001 - never crash the app on a check
        logger.debug("Update check failed: %s", exc)
        return UpdateInfo(current=current, latest=current, available=False)

    if isinstance(releases, dict):          # a single-release payload
        releases = [releases]
    best = None
    for rel in releases or []:
        if rel.get("draft"):
            continue
        if rel.get("prerelease") and not include_prerelease:
            continue
        tag = rel.get("tag_name", "")
        if best is None or is_newer(tag, best.get("tag_name", "")):
            best = rel
    if best is None:
        return UpdateInfo(current=current, latest=current, available=False)

    latest = best.get("tag_name", "")
    return UpdateInfo(
        current=current, latest=latest,
        available=is_newer(latest, current),
        url=best.get("html_url", ""),
        download_url=_pick_asset(best.get("assets", []), asset_suffix),
        notes=best.get("body", "") or "",
        channel="github",
        prerelease=bool(best.get("prerelease")),
    )
