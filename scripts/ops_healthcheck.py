#!/usr/bin/env python3
"""Ops healthcheck: aggregate daily/LLM/disk/key/quality/deploy into ops-status.json.

Usage:
    python3 scripts/ops_healthcheck.py
    python3 scripts/ops_healthcheck.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT

# Configurable job ids (may be updated without code rewrite of callers)
DEFAULT_CRON_JOBS = {
    "daily": "2a0c271a031f",
    "llm_daily": "f110f12e4d96",
    "weekly": "2aa9da554787",
}

DISK_WARN_GB = 5.0
DISK_FAIL_GB = 1.0
DEPLOY_WARN_HOURS = 48.0
CRON_STALE_HOURS = 36.0  # daily should run every ~24h
DEFAULT_WEBROOT_METRICS = Path("/var/www/ecoradar.lzpgood.online/data/metrics.json")
DEFAULT_CRON_OUTPUT = Path.home() / ".hermes" / "cron" / "output"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def evaluate_status(signals: dict[str, Any]) -> dict[str, Any]:
    """Pure evaluation of health signals -> level + checks[].

    signals keys:
      last_daily_ok: bool | None
      last_llm_ok: bool | None
      disk_free_gb: float | None
      llm_degraded: bool
      quality_gate: str | None  # PASS/FAIL/UNKNOWN
      deploy_age_hours: float | None
      failed_onboards: int
      daily_age_hours: float | None  (optional)
      llm_age_hours: float | None    (optional)
    """
    checks: list[dict[str, str]] = []
    hints: list[str] = []

    # daily
    daily_ok = signals.get("last_daily_ok")
    daily_age = signals.get("daily_age_hours")
    if daily_ok is False:
        checks.append({"id": "daily", "level": "fail", "message": "最近 daily 采集失败"})
        hints.append("检查 agent-ecoradar-daily.sh / cron output")
    elif daily_ok is None:
        checks.append({"id": "daily", "level": "warn", "message": "找不到 daily cron 输出"})
    elif daily_age is not None and daily_age > CRON_STALE_HOURS:
        checks.append(
            {
                "id": "daily",
                "level": "warn",
                "message": f"daily 输出过旧 ({daily_age:.1f}h)",
            }
        )
    else:
        checks.append({"id": "daily", "level": "ok", "message": "daily 最近运行成功"})

    # llm (daily incremental or weekly — treat missing as warn, not fail on Mon-only)
    llm_ok = signals.get("last_llm_ok")
    llm_age = signals.get("llm_age_hours")
    if llm_ok is False:
        checks.append({"id": "llm", "level": "fail", "message": "最近 LLM job 失败"})
        hints.append("检查 llm-daily/weekly 脚本与 SenseNova key")
    elif llm_ok is None:
        checks.append({"id": "llm", "level": "warn", "message": "找不到 LLM cron 输出"})
    elif llm_age is not None and llm_age > 96:  # weekend gap ok; >4d stale
        checks.append(
            {
                "id": "llm",
                "level": "warn",
                "message": f"LLM 输出过旧 ({llm_age:.1f}h)",
            }
        )
    else:
        checks.append({"id": "llm", "level": "ok", "message": "LLM 最近运行成功"})

    # disk
    free_gb = signals.get("disk_free_gb")
    if free_gb is None:
        checks.append({"id": "disk", "level": "warn", "message": "无法读取磁盘空间"})
    elif free_gb < DISK_FAIL_GB:
        checks.append(
            {
                "id": "disk",
                "level": "fail",
                "message": f"根分区仅剩 {free_gb:.2f} GiB",
            }
        )
        hints.append("立即运行 cleanup_disk 或扩容")
    elif free_gb < DISK_WARN_GB:
        checks.append(
            {
                "id": "disk",
                "level": "warn",
                "message": f"根分区剩余 {free_gb:.2f} GiB（预警）",
            }
        )
        hints.append("考虑 cleanup_disk --apply")
    else:
        checks.append(
            {
                "id": "disk",
                "level": "ok",
                "message": f"根分区剩余 {free_gb:.2f} GiB",
            }
        )

    # llm keys degraded
    if signals.get("llm_degraded"):
        checks.append(
            {
                "id": "llm_keys",
                "level": "warn",
                "message": "LLM 处于 degraded 模式或近期 429",
            }
        )
    else:
        checks.append({"id": "llm_keys", "level": "ok", "message": "LLM key 状态正常"})

    # quality gate
    qg = (signals.get("quality_gate") or "UNKNOWN").upper()
    if qg == "FAIL":
        checks.append({"id": "quality_gate", "level": "fail", "message": "quality_gate FAIL"})
        hints.append("勿 deploy；修数据/门禁后重建")
    elif qg == "PASS":
        checks.append({"id": "quality_gate", "level": "ok", "message": "quality_gate PASS"})
    else:
        checks.append(
            {
                "id": "quality_gate",
                "level": "warn",
                "message": f"quality_gate 未知 ({qg})",
            }
        )

    # deploy freshness
    deploy_age = signals.get("deploy_age_hours")
    if deploy_age is None:
        checks.append(
            {
                "id": "deploy",
                "level": "warn",
                "message": "webroot metrics 不存在或不可读",
            }
        )
    elif deploy_age > DEPLOY_WARN_HOURS:
        checks.append(
            {
                "id": "deploy",
                "level": "warn",
                "message": f"站点 metrics 已 {deploy_age:.1f}h 未更新",
            }
        )
    else:
        checks.append(
            {
                "id": "deploy",
                "level": "ok",
                "message": f"站点 metrics 新鲜 ({deploy_age:.1f}h)",
            }
        )

    # failed onboards
    failed_onboards = int(signals.get("failed_onboards") or 0)
    if failed_onboards > 0:
        checks.append(
            {
                "id": "onboard",
                "level": "warn",
                "message": f"{failed_onboards} 个工具 onboard_state=failed",
            }
        )
        hints.append("重试 failed onboard 或人工处理")
    else:
        checks.append({"id": "onboard", "level": "ok", "message": "无 failed onboard"})

    levels = [c["level"] for c in checks]
    if "fail" in levels:
        level = "fail"
    elif "warn" in levels:
        level = "warn"
    else:
        level = "ok"

    return {
        "level": level,
        "checks": checks,
        "hints": hints,
    }


def parse_latest_cron_run(
    cron_output_dir: Path, job_id: str
) -> tuple[Optional[bool], Optional[float], Optional[Path]]:
    """Return (ok, age_hours, path) for the newest .md under job output dir."""
    job_dir = Path(cron_output_dir) / job_id
    if not job_dir.is_dir():
        return None, None, None
    files = sorted(job_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None, None, None
    path = files[0]
    text = path.read_text(encoding="utf-8", errors="replace")
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    age_hours = (_now() - mtime).total_seconds() / 3600.0

    title = text.splitlines()[0] if text else ""
    lower = text.lower()
    if "(failed)" in title.lower() or "**status:** fail" in lower:
        ok = False
    elif re.search(r'"status"\s*:\s*"PASS"', text) or "exit=0" in text:
        ok = True
    elif "error" in lower and "returncode" in lower and re.search(
        r'"returncode"\s*:\s*(?!0\b)\d+', text
    ):
        # any non-zero required step is fail-ish; keep simple: look for FAILED
        ok = False if "failed" in lower else True
    else:
        # no_agent script success usually ends without FAILED marker
        ok = "(failed)" not in title.lower() and "traceback" not in lower
    return ok, age_hours, path


def parse_quality_gate_from_text(text: str) -> str:
    if re.search(r'"status"\s*:\s*"PASS"', text):
        return "PASS"
    if re.search(r'"status"\s*:\s*"FAIL"', text) or "quality_gate fail" in text.lower():
        return "FAIL"
    if "quality_gate" in text.lower() and "pass" in text.lower():
        return "PASS"
    return "UNKNOWN"


def read_llm_degraded(stats_path: Path) -> bool:
    if not stats_path.exists():
        return False
    try:
        data = json.loads(stats_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if isinstance(data, list) and data:
        last = data[-1]
        if isinstance(last, dict):
            if last.get("degraded_mode"):
                return True
            if int(last.get("429_errors") or 0) > 0:
                return True
    elif isinstance(data, dict):
        if data.get("degraded_mode"):
            return True
    return False


def count_failed_onboards(seed_path: Path) -> int:
    if not seed_path.exists():
        return 0
    try:
        import yaml

        data = yaml.safe_load(seed_path.read_text(encoding="utf-8"))
    except Exception:
        # naive fallback
        text = seed_path.read_text(encoding="utf-8", errors="replace")
        return len(re.findall(r"onboard_state:\s*failed", text))
    if not isinstance(data, list):
        return 0
    n = 0
    for item in data:
        if isinstance(item, dict) and item.get("onboard_state") == "failed":
            n += 1
    return n


def deploy_age_hours(metrics_path: Path) -> Optional[float]:
    if not metrics_path.exists():
        return None
    mtime = datetime.fromtimestamp(metrics_path.stat().st_mtime, tz=timezone.utc)
    return (_now() - mtime).total_seconds() / 3600.0


def disk_free_gb(path: Path | str = "/") -> Optional[float]:
    try:
        usage = shutil.disk_usage(path)
        return usage.free / (1024 ** 3)
    except OSError:
        return None


def collect_signals(
    *,
    root: Path = ROOT,
    cron_output_dir: Path = DEFAULT_CRON_OUTPUT,
    job_ids: Optional[dict[str, str]] = None,
    webroot_metrics: Path = DEFAULT_WEBROOT_METRICS,
) -> dict[str, Any]:
    jobs = dict(DEFAULT_CRON_JOBS)
    if job_ids:
        jobs.update(job_ids)

    daily_ok, daily_age, daily_path = parse_latest_cron_run(cron_output_dir, jobs["daily"])
    llm_ok, llm_age, llm_path = parse_latest_cron_run(cron_output_dir, jobs["llm_daily"])
    # if llm_daily missing, fall back to weekly output
    if llm_ok is None:
        llm_ok, llm_age, llm_path = parse_latest_cron_run(cron_output_dir, jobs["weekly"])

    qg = "UNKNOWN"
    for p in (daily_path, llm_path):
        if p and p.exists():
            qg = parse_quality_gate_from_text(p.read_text(encoding="utf-8", errors="replace"))
            if qg != "UNKNOWN":
                break

    signals = {
        "last_daily_ok": daily_ok,
        "last_llm_ok": llm_ok,
        "daily_age_hours": daily_age,
        "llm_age_hours": llm_age,
        "disk_free_gb": disk_free_gb("/"),
        "llm_degraded": read_llm_degraded(root / "data" / "llm-key-stats.json"),
        "quality_gate": qg,
        "deploy_age_hours": deploy_age_hours(webroot_metrics),
        "failed_onboards": count_failed_onboards(root / "data" / "seed-tools.yaml"),
        "raw_data_exists": (root / "data" / "raw").exists(),
        "snapshots_exists": (root / "data" / "snapshots").exists(),
        "job_ids": jobs,
        "daily_output": str(daily_path) if daily_path else None,
        "llm_output": str(llm_path) if llm_path else None,
    }
    return signals


def build_status_document(signals: dict[str, Any]) -> dict[str, Any]:
    evaluated = evaluate_status(signals)
    return {
        "ts": _now().isoformat(),
        "level": evaluated["level"],
        "checks": evaluated["checks"],
        "hints": evaluated["hints"],
        "signals": {
            k: v
            for k, v in signals.items()
            if k
            not in (
                # keep compact; full paths optional
            )
        },
    }


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Agent EcoRadar ops healthcheck")
    ap.add_argument("--dry-run", action="store_true", help="不写 data/ops-status.json")
    ap.add_argument(
        "--output",
        default=str(ROOT / "data" / "ops-status.json"),
        help="status 输出路径",
    )
    ap.add_argument(
        "--cron-output",
        default=str(DEFAULT_CRON_OUTPUT),
        help="Hermes cron output 根目录",
    )
    ap.add_argument(
        "--metrics",
        default=str(DEFAULT_WEBROOT_METRICS),
        help="线上 metrics.json 路径（deploy 新鲜度）",
    )
    args = ap.parse_args(argv)

    signals = collect_signals(
        root=ROOT,
        cron_output_dir=Path(args.cron_output),
        webroot_metrics=Path(args.metrics),
    )
    doc = build_status_document(signals)
    text = json.dumps(doc, ensure_ascii=False, indent=2)
    print(text)
    if not args.dry_run:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    return 0 if doc["level"] != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
