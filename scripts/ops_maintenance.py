#!/usr/bin/env python3
"""Ops maintenance: archive + cleanup orchestration.

Usage:
    python3 scripts/ops_maintenance.py --dry-run
    python3 scripts/ops_maintenance.py --apply
    python3 scripts/ops_maintenance.py --apply --skip-archive
    python3 scripts/ops_maintenance.py --apply --skip-cleanup
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT


def _run_script(
    root: Path,
    script_name: str,
    apply: bool,
    extra_args: Optional[list[str]] = None,
    timeout: int = 1800,
) -> dict[str, Any]:
    script = root / "scripts" / script_name
    cmd = [sys.executable, str(script)]
    if apply:
        cmd.append("--apply")
    if extra_args:
        cmd.extend(extra_args)
    proc = subprocess.run(
        cmd,
        cwd=str(root),
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "")[-4000:],
        "stderr": (proc.stderr or "")[-2000:],
    }


def run_maintenance(
    *,
    apply: bool = False,
    skip_archive: bool = False,
    skip_cleanup: bool = False,
    root: Path = ROOT,
    archive_extra: Optional[list[str]] = None,
    cleanup_extra: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Run archive then cleanup. Returns summary with ok bool."""
    archive_result = None
    cleanup_result = None

    if not skip_archive:
        archive_result = _run_script(
            root, "archive_low_score.py", apply=apply, extra_args=archive_extra
        )
    if not skip_cleanup:
        cleanup_result = _run_script(
            root, "cleanup_disk.py", apply=apply, extra_args=cleanup_extra
        )

    codes = []
    if archive_result is not None:
        codes.append(archive_result["returncode"])
    if cleanup_result is not None:
        codes.append(cleanup_result["returncode"])
    ok = all(c == 0 for c in codes) if codes else True

    return {
        "apply": apply,
        "archive": archive_result,
        "cleanup": cleanup_result,
        "ok": ok,
    }


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Agent EcoRadar ops maintenance")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="不传 --apply 给子脚本（默认即 dry-run，除非 --apply）",
    )
    ap.add_argument("--apply", action="store_true", help="真正执行 archive/cleanup")
    ap.add_argument("--skip-archive", action="store_true")
    ap.add_argument("--skip-cleanup", action="store_true")
    ap.add_argument(
        "--threshold",
        type=int,
        default=None,
        help="传给 archive_low_score --threshold",
    )
    args = ap.parse_args(argv)

    apply = bool(args.apply) and not args.dry_run
    archive_extra = None
    if args.threshold is not None:
        archive_extra = ["--threshold", str(args.threshold)]

    result = run_maintenance(
        apply=apply,
        skip_archive=args.skip_archive,
        skip_cleanup=args.skip_cleanup,
        root=ROOT,
        archive_extra=archive_extra,
    )
    # compact printable summary
    printable = {
        "apply": result["apply"],
        "ok": result["ok"],
        "archive": None
        if result["archive"] is None
        else {
            "returncode": result["archive"]["returncode"],
            "stdout_tail": result["archive"]["stdout"][-800:],
            "stderr_tail": result["archive"]["stderr"][-400:],
        },
        "cleanup": None
        if result["cleanup"] is None
        else {
            "returncode": result["cleanup"]["returncode"],
            "stdout_tail": result["cleanup"]["stdout"][-800:],
            "stderr_tail": result["cleanup"]["stderr"][-400:],
        },
    }
    print(json.dumps(printable, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
