#!/usr/bin/env python3
"""Auto-bump VERSION and CHANGELOG.md on data changes."""
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"
CHANGELOG_FILE = ROOT / "CHANGELOG.md"

today = date.today().strftime("%Y.%m.%d")

# Read current version
current_version = VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else ""

# Only bump if today is different from current version
if current_version == today:
    print(f"Version already {today}, skipping bump")
    exit(0)

# Write new version
VERSION_FILE.write_text(f"{today}\n")

# Prepend new changelog entry
new_entry = f"""## {today} — 自动更新

### Changed

- 数据自动采集更新。

### Data

- `data/raw/` 新增当日采集记录。
- `data/curated/`、`data/reports/` 自动重新生成。

"""

existing = CHANGELOG_FILE.read_text(encoding="utf-8") if CHANGELOG_FILE.exists() else "# Changelog\n\n"
CHANGELOG_FILE.write_text(new_entry + existing, encoding="utf-8")

print(f"Bumped version: {current_version} -> {today}")