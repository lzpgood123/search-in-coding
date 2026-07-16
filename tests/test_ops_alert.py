"""Test ops_alert debounce and recovery."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def _status(level: str, checks=None):
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "checks": checks
        or [{"id": "daily", "level": level, "message": f"daily {level}"}],
        "hints": ["hint"],
    }


class TestOpsAlert:
    def test_ok_no_alert(self, tmp_path):
        from ops_alert import decide_alert

        status = _status("ok")
        decision = decide_alert(status, state={}, cooldown_hours=6)
        assert decision["should_alert"] is False
        assert decision["kind"] is None

    def test_fail_first_alerts(self, tmp_path):
        from ops_alert import decide_alert

        status = _status("fail")
        decision = decide_alert(status, state={}, cooldown_hours=6)
        assert decision["should_alert"] is True
        assert decision["kind"] == "alert"

    def test_same_fail_within_cooldown_no_repeat(self, tmp_path):
        from ops_alert import decide_alert, fingerprint

        status = _status("fail")
        fp = fingerprint(status)
        state = {
            "last_level": "fail",
            "last_fingerprint": fp,
            "last_alert_ts": datetime.now(timezone.utc).isoformat(),
            "last_kind": "alert",
        }
        decision = decide_alert(status, state=state, cooldown_hours=6)
        assert decision["should_alert"] is False

    def test_same_fail_after_cooldown_alerts(self, tmp_path):
        from ops_alert import decide_alert, fingerprint

        status = _status("fail")
        fp = fingerprint(status)
        old = (datetime.now(timezone.utc) - timedelta(hours=7)).isoformat()
        state = {
            "last_level": "fail",
            "last_fingerprint": fp,
            "last_alert_ts": old,
            "last_kind": "alert",
        }
        decision = decide_alert(status, state=state, cooldown_hours=6)
        assert decision["should_alert"] is True

    def test_fail_to_ok_recovery(self, tmp_path):
        from ops_alert import decide_alert

        status = _status("ok")
        state = {
            "last_level": "fail",
            "last_fingerprint": "x",
            "last_alert_ts": datetime.now(timezone.utc).isoformat(),
            "last_kind": "alert",
        }
        decision = decide_alert(status, state=state, cooldown_hours=6)
        assert decision["should_alert"] is True
        assert decision["kind"] == "recovery"

    def test_write_alert_file_and_state(self, tmp_path):
        from ops_alert import process_status

        status_path = tmp_path / "ops-status.json"
        status = _status("fail")
        status_path.write_text(json.dumps(status), encoding="utf-8")
        result = process_status(
            status_path=status_path,
            state_path=tmp_path / "ops-alert-state.json",
            alerts_dir=tmp_path / "ops-alerts",
            cooldown_hours=6,
            stdout_on_alert=False,
        )
        assert result["should_alert"] is True
        assert result["alert_file"] is not None
        assert Path(result["alert_file"]).exists()
        state = json.loads((tmp_path / "ops-alert-state.json").read_text(encoding="utf-8"))
        assert state["last_level"] == "fail"
