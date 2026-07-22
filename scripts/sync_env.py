#!/usr/bin/env python3
"""
Append keys that are new in .env.example into your existing .env.

Your .env is not tracked by git (it holds secrets), so `git pull` never updates
it. Run this after pulling to add any newly introduced settings — with their
example defaults and comments — WITHOUT touching your existing values:

    python3 scripts/sync_env.py            # updates ./.env in place
    python3 scripts/sync_env.py --check    # only report what's missing

A timestamped backup (.env.bak) is written before any change.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import time
from pathlib import Path

KEY_RE = re.compile(r"^([A-Z][A-Z0-9_]*)=")


def keys_in(path: Path) -> set[str]:
    keys: set[str] = set()
    if not path.exists():
        return keys
    for line in path.read_text(encoding="utf-8").splitlines():
        m = KEY_RE.match(line.strip())
        if m:
            keys.add(m.group(1))
    return keys


def missing_blocks(example: Path, have: set[str]) -> tuple[list[str], list[str]]:
    """Return (appended_lines, added_keys) for keys not already present."""
    lines = example.read_text(encoding="utf-8").splitlines()
    appended: list[str] = []
    added: list[str] = []
    for i, line in enumerate(lines):
        m = KEY_RE.match(line.strip())
        if not m or m.group(1) in have:
            continue
        key = m.group(1)
        # Grab the contiguous comment lines directly above for context.
        comments: list[str] = []
        j = i - 1
        while j >= 0 and lines[j].lstrip().startswith("#"):
            comments.insert(0, lines[j])
            j -= 1
        if comments:
            appended.extend(comments)
        appended.append(line)
        appended.append("")
        added.append(key)
    return appended, added


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default=".env")
    ap.add_argument("--example", default=".env.example")
    ap.add_argument("--check", action="store_true",
                    help="only report missing keys, don't modify")
    args = ap.parse_args()

    env, example = Path(args.env), Path(args.example)
    if not example.exists():
        print(f"❌ {example} not found (run from the project root).")
        return 1
    if not env.exists():
        print(f"❌ {env} not found. Create it first: cp {example} {env}")
        return 1

    have = keys_in(env)
    appended, added = missing_blocks(example, have)

    if not added:
        print("✅ Your .env already has every key from .env.example.")
        return 0

    print(f"🔎 {len(added)} new key(s): {', '.join(added)}")
    if args.check:
        return 0

    backup = Path(f"{env}.bak.{int(time.time())}")
    shutil.copy2(env, backup)
    with env.open("a", encoding="utf-8") as fh:
        fh.write("\n\n# ============================================\n")
        fh.write("#  Added by sync_env.py (new since your .env)\n")
        fh.write("# ============================================\n")
        fh.write("\n".join(appended).rstrip() + "\n")
    print(f"✅ Appended {len(added)} key(s) to {env} (backup: {backup.name}).")
    print("   Fill in the blanks you need, then restart:")
    print("   docker compose up -d --force-recreate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
