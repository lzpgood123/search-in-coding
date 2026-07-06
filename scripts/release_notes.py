#!/usr/bin/env python3
"""Extract the latest changelog entry for a GitHub Release."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def extract_latest_changelog() -> str | None:
    changelog = ROOT / "CHANGELOG.md"
    if not changelog.exists():
        return None
    text = changelog.read_text(encoding="utf-8")
    m = re.search(r'^##\s+(.+?)\n\n(.+?)(?=\n##\s+|\Z)', text, re.DOTALL | re.MULTILINE)
    if m:
        return m.group(2).strip()
    return None


def main():
    version = (ROOT / "VERSION").read_text().strip()
    notes = extract_latest_changelog()
    print(f"version={version}")
    print(f"tag=v{version}")
    print(f"notes<<EOF_HERMES")
    print(notes or "No changelog entry found.")
    print("EOF_HERMES")


if __name__ == "__main__":
    main()