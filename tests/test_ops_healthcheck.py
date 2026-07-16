"""Test ops_healthcheck pure logic and signal collection."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


class TestEvaluateStatus:
    def test_all_green_is_ok(self):
        from ops_healthcheck import evaluate_status

        result = evaluate_status(
            {
                "last_daily_ok": True,
                "last_llm_ok": True,
                "disk_free_gb": 12.0,
                "llm_degraded": False,
                "quality_gate": "PASS",
                "deploy_age_hours": 6.0,
                "failed_onboards": 0,
            }
        )
        assert result["level"] == "ok"
        assert all(c["level"] == "ok" for c in result["checks"])

    def test_critical_failure_is_fail(self):
        from ops_healthcheck import evaluate_status

        result = evaluate_status(
            {
                "last_daily_ok": False,
                "last_llm_ok": True,
                "disk_free_gb": 12.0,
                "llm_degraded": False,
                "quality_gate": "PASS",
                "deploy_age_hours": 6.0,
                "failed_onboards": 0,
            }
        )
        assert result["level"] == "fail"
        daily = next(c for c in result["checks"] if c["id"] == "daily")
        assert daily["level"] == "fail"

    def test_degraded_or_disk_warn(self):
        from ops_healthcheck import evaluate_status

        result = evaluate_status(
            {
                "last_daily_ok": True,
                "last_llm_ok": True,
                "disk_free_gb": 3.5,
                "llm_degraded": True,
                "quality_gate": "PASS",
                "deploy_age_hours": 6.0,
                "failed_onboards": 0,
            }
        )
        assert result["level"] == "warn"
        disk = next(c for c in result["checks"] if c["id"] == "disk")
        llm = next(c for c in result["checks"] if c["id"] == "llm_keys")
        assert disk["level"] == "warn"
        assert llm["level"] == "warn"

    def test_quality_gate_fail_is_fail(self):
        from ops_healthcheck import evaluate_status

        result = evaluate_status(
            {
                "last_daily_ok": True,
                "last_llm_ok": True,
                "disk_free_gb": 12.0,
                "llm_degraded": False,
                "quality_gate": "FAIL",
                "deploy_age_hours": 6.0,
                "failed_onboards": 0,
            }
        )
        assert result["level"] == "fail"
        qg = next(c for c in result["checks"] if c["id"] == "quality_gate")
        assert qg["level"] == "fail"

    def test_failed_onboards_warn(self):
        from ops_healthcheck import evaluate_status

        result = evaluate_status(
            {
                "last_daily_ok": True,
                "last_llm_ok": True,
                "disk_free_gb": 12.0,
                "llm_degraded": False,
                "quality_gate": "PASS",
                "deploy_age_hours": 6.0,
                "failed_onboards": 2,
            }
        )
        assert result["level"] == "warn"
        onboard = next(c for c in result["checks"] if c["id"] == "onboard")
        assert onboard["level"] == "warn"

    def test_stale_deploy_warn(self):
        from ops_healthcheck import evaluate_status

        result = evaluate_status(
            {
                "last_daily_ok": True,
                "last_llm_ok": True,
                "disk_free_gb": 12.0,
                "llm_degraded": False,
                "quality_gate": "PASS",
                "deploy_age_hours": 72.0,
                "failed_onboards": 0,
            }
        )
        assert result["level"] == "warn"
        deploy = next(c for c in result["checks"] if c["id"] == "deploy")
        assert deploy["level"] == "warn"

    def test_missing_deploy_is_warn(self):
        from ops_healthcheck import evaluate_status

        result = evaluate_status(
            {
                "last_daily_ok": True,
                "last_llm_ok": True,
                "disk_free_gb": 12.0,
                "llm_degraded": False,
                "quality_gate": "PASS",
                "deploy_age_hours": None,
                "failed_onboards": 0,
            }
        )
        assert result["level"] == "warn"
        deploy = next(c for c in result["checks"] if c["id"] == "deploy")
        assert deploy["level"] == "warn"


class TestCollectSignals:
    def test_parse_latest_cron_success(self, tmp_path):
        from ops_healthcheck import parse_latest_cron_run

        job_dir = tmp_path / "2a0c271a031f"
        job_dir.mkdir()
        (job_dir / "2026-07-16_03-28-52.md").write_text(
            "# Cron Job: daily\n\n**Run Time:** 2026-07-16 03:28:52\n\n"
            '{"status": "PASS", "deploy": false}\n',
            encoding="utf-8",
        )
        ok, age_hours, path = parse_latest_cron_run(tmp_path, "2a0c271a031f")
        assert ok is True
        assert path is not None
        assert age_hours is not None
        assert age_hours >= 0

    def test_parse_latest_cron_failed_marker(self, tmp_path):
        from ops_healthcheck import parse_latest_cron_run

        job_dir = tmp_path / "2a0c271a031f"
        job_dir.mkdir()
        (job_dir / "2026-07-16_03-00-00.md").write_text(
            "# Cron Job: daily (FAILED)\n\nerror boom\n",
            encoding="utf-8",
        )
        ok, _age, path = parse_latest_cron_run(tmp_path, "2a0c271a031f")
        assert ok is False
        assert path is not None

    def test_parse_missing_job_dir(self, tmp_path):
        from ops_healthcheck import parse_latest_cron_run

        ok, age, path = parse_latest_cron_run(tmp_path, "missing")
        assert ok is None
        assert age is None
        assert path is None

    def test_read_llm_degraded_true(self, tmp_path):
        from ops_healthcheck import read_llm_degraded

        p = tmp_path / "llm-key-stats.json"
        p.write_text(
            json.dumps(
                [
                    {"date": "2026-07-14", "degraded_mode": False},
                    {"date": "2026-07-15", "degraded_mode": True, "429_errors": 3},
                ]
            ),
            encoding="utf-8",
        )
        assert read_llm_degraded(p) is True

    def test_read_llm_degraded_false(self, tmp_path):
        from ops_healthcheck import read_llm_degraded

        p = tmp_path / "llm-key-stats.json"
        p.write_text(
            json.dumps([{"date": "2026-07-15", "degraded_mode": False}]),
            encoding="utf-8",
        )
        assert read_llm_degraded(p) is False

    def test_count_failed_onboards(self, tmp_path):
        from ops_healthcheck import count_failed_onboards

        p = tmp_path / "seed-tools.yaml"
        p.write_text(
            "- id: a\n  onboard_state: done\n"
            "- id: b\n  onboard_state: failed\n"
            "- id: c\n  onboard_state: pending\n"
            "- id: d\n  onboard_state: failed\n",
            encoding="utf-8",
        )
        assert count_failed_onboards(p) == 2

    def test_deploy_age_from_metrics(self, tmp_path):
        from ops_healthcheck import deploy_age_hours

        metrics = tmp_path / "metrics.json"
        metrics.write_text("{}", encoding="utf-8")
        # touch mtime to ~2h ago
        past = (datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()
        import os

        os.utime(metrics, (past, past))
        age = deploy_age_hours(metrics)
        assert age is not None
        assert 1.5 <= age <= 3.0

    def test_quality_gate_from_cron_output(self, tmp_path):
        from ops_healthcheck import parse_quality_gate_from_text

        text = '{\"status\": \"PASS\", \"errors\": []}'
        assert parse_quality_gate_from_text(text) == "PASS"
        text2 = "# Cron (FAILED)\nquality_gate FAIL"
        assert parse_quality_gate_from_text(text2) in ("FAIL", "UNKNOWN")
