#!/usr/bin/env python3
"""Ops alert with debounce; local files + optional stdout for cron deliver.

Usage:
    python3 scripts/ops_alert.py
    python3 scripts/ops_alert.py --stdout-on-alert
    python3 scripts/ops_alert.py --status path --state path --alerts-dir path
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT

DEFAULT_STATUS = ROOT / "data" / "ops-status.json"
DEFAULT_STATE = ROOT / "data" / "ops-alert-state.json"
DEFAULT_ALERTS = ROOT / "data" / "ops-alerts"
DEFAULT_COOLDOWN_HOURS = 6.0


def _parse_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        # support Z and offset
        t = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(t)
    except ValueError:
        return None


def fingerprint(status: dict[str, Any]) -> str:
    """Stable fingerprint of level + check levels/messages."""
    parts = [str(status.get("level") or "")]
    for c in status.get("checks") or []:
        if not isinstance(c, dict):
            continue
        parts.append(f"{c.get('id')}|{c.get('level')}|{c.get('message')}")
    raw = "\n".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def decide_alert(
    status: dict[str, Any],
    state: dict[str, Any],
    cooldown_hours: float = DEFAULT_COOLDOWN_HOURS,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Decide whether to emit alert/recovery.

    Rules:
    - ok and previous was not fail/warn needing recovery: no alert
    - fail/warn first time: alert
    - same fingerprint within cooldown: no alert
    - fail/warn -> ok: recovery once
    """
    now = now or datetime.now(timezone.utc)
    level = (status.get("level") or "ok").lower()
    fp = fingerprint(status)
    last_level = (state.get("last_level") or "ok").lower()
    last_fp = state.get("last_fingerprint")
    last_ts = _parse_ts(state.get("last_alert_ts"))

    # Recovery: was fail (or warn) and now ok
    if level == "ok":
        if last_level in ("fail", "warn") and state.get("last_kind") == "alert":
            return {
                "should_alert": True,
                "kind": "recovery",
                "fingerprint": fp,
                "level": level,
                "reason": f"recovered from {last_level}",
            }
        return {
            "should_alert": False,
            "kind": None,
            "fingerprint": fp,
            "level": level,
            "reason": "healthy",
        }

    # warn/fail
    if last_fp == fp and last_ts is not None:
        age_h = (now - last_ts.astimezone(timezone.utc)).total_seconds() / 3600.0
        if age_h < cooldown_hours:
            return {
                "should_alert": False,
                "kind": None,
                "fingerprint": fp,
                "level": level,
                "reason": f"cooldown ({age_h:.1f}h < {cooldown_hours}h)",
            }

    return {
        "should_alert": True,
        "kind": "alert",
        "fingerprint": fp,
        "level": level,
        "reason": "new or cooled-down issue",
    }


def format_alert_body(status: dict[str, Any], kind: str) -> str:
    level = status.get("level")
    ts = status.get("ts")
    lines = [
        f"# Agent EcoRadar ops {kind}",
        "",
        f"- level: **{level}**",
        f"- status_ts: {ts}",
        f"- kind: {kind}",
        "",
        "## Checks",
        "",
    ]
    for c in status.get("checks") or []:
        if isinstance(c, dict):
            lines.append(f"- [{c.get('level')}] `{c.get('id')}`: {c.get('message')}")
    hints = status.get("hints") or []
    if hints:
        lines.extend(["", "## Hints", ""])
        for h in hints:
            lines.append(f"- {h}")
    lines.append("")
    lines.append("本地状态: `data/ops-status.json`")
    lines.append("")
    return "\n".join(lines)


def process_status(
    *,
    status_path: Path,
    state_path: Path,
    alerts_dir: Path,
    cooldown_hours: float = DEFAULT_COOLDOWN_HOURS,
    stdout_on_alert: bool = False,
) -> dict[str, Any]:
    if not status_path.exists():
        return {
            "should_alert": False,
            "kind": None,
            "error": f"missing status: {status_path}",
            "alert_file": None,
            "stdout": "",
        }
    status = json.loads(status_path.read_text(encoding="utf-8"))
    state: dict[str, Any] = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {}

    decision = decide_alert(status, state=state, cooldown_hours=cooldown_hours)
    alert_file = None
    stdout_text = ""

    if decision["should_alert"]:
        body = format_alert_body(status, decision["kind"] or "alert")
        alerts_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
        alert_file = alerts_dir / f"{stamp}.md"
        alert_file.write_text(body, encoding="utf-8")

        new_state = {
            "last_level": decision["level"],
            "last_fingerprint": decision["fingerprint"],
            "last_alert_ts": datetime.now(timezone.utc).isoformat(),
            "last_kind": decision["kind"],
            "last_alert_file": str(alert_file),
        }
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(new_state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if stdout_on_alert:
            # cron no_agent: non-empty stdout is delivered
            prefix = "ALERT:" if decision["kind"] == "alert" else "RECOVERY:"
            stdout_text = f"{prefix}\n{body}"
    else:
        # still refresh last seen level without resetting cooldown fingerprint on pure ok
        if decision["level"] == "ok" and (state.get("last_level") or "ok") == "ok":
            pass

    return {
        "should_alert": decision["should_alert"],
        "kind": decision["kind"],
        "level": decision["level"],
        "reason": decision.get("reason"),
        "fingerprint": decision.get("fingerprint"),
        "alert_file": str(alert_file) if alert_file else None,
        "stdout": stdout_text,
    }


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Agent EcoRadar ops alert")
    ap.add_argument("--status", default=str(DEFAULT_STATUS))
    ap.add_argument("--state", default=str(DEFAULT_STATE))
    ap.add_argument("--alerts-dir", default=str(DEFAULT_ALERTS))
    ap.add_argument("--cooldown-hours", type=float, default=DEFAULT_COOLDOWN_HOURS)
    ap.add_argument(
        "--stdout-on-alert",
        action="store_true",
        help="仅在需要告警/恢复时向 stdout 打印全文（供 no_agent cron 投递）",
    )
    args = ap.parse_args(argv)

    result = process_status(
        status_path=Path(args.status),
        state_path=Path(args.state),
        alerts_dir=Path(args.alerts_dir),
        cooldown_hours=args.cooldown_hours,
        stdout_on_alert=args.stdout_on_alert,
    )

    # Always print machine-readable one-liner to stderr for logs; stdout only for deliver
    summary = {
        "should_alert": result["should_alert"],
        "kind": result["kind"],
        "level": result.get("level"),
        "reason": result.get("reason"),
        "alert_file": result.get("alert_file"),
    }
    print(json.dumps(summary, ensure_ascii=False), file=sys.stderr)
    if result.get("stdout"):
        # bare alert body to stdout for cron deliver
        sys.stdout.write(result["stdout"])
        if not result["stdout"].endswith("\n"):
            sys.stdout.write("\n")
    # exit 0 always for alert path (delivery is content-based); missing status is warn
    return 0 if not result.get("error") else 1


if __name__ == "__main__":
    raise SystemExit(main())
