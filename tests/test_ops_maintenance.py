"""Test ops_maintenance orchestration."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


class TestOpsMaintenance:
    def test_dry_run_order_archive_then_cleanup(self):
        from ops_maintenance import run_maintenance

        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            m = MagicMock()
            m.returncode = 0
            m.stdout = json.dumps({"ok": True, "apply": "--apply" not in cmd})
            m.stderr = ""
            return m

        with patch("ops_maintenance.subprocess.run", side_effect=fake_run):
            result = run_maintenance(apply=False, root=Path("/tmp/proj"))

        assert result["ok"] is True
        assert len(calls) == 2
        assert "archive_low_score.py" in calls[0][1] or "archive_low_score.py" in " ".join(
            calls[0]
        )
        assert "cleanup_disk.py" in " ".join(calls[1])
        # dry-run: no --apply
        assert "--apply" not in calls[0]
        assert "--apply" not in calls[1]

    def test_apply_passes_apply_flag(self):
        from ops_maintenance import run_maintenance

        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            m = MagicMock()
            m.returncode = 0
            m.stdout = "{}"
            m.stderr = ""
            return m

        with patch("ops_maintenance.subprocess.run", side_effect=fake_run):
            result = run_maintenance(apply=True, root=Path("/tmp/proj"))

        assert result["ok"] is True
        assert "--apply" in calls[0]
        assert "--apply" in calls[1]

    def test_skip_archive(self):
        from ops_maintenance import run_maintenance

        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            m = MagicMock()
            m.returncode = 0
            m.stdout = "{}"
            m.stderr = ""
            return m

        with patch("ops_maintenance.subprocess.run", side_effect=fake_run):
            result = run_maintenance(apply=False, skip_archive=True, root=Path("/tmp/proj"))

        assert len(calls) == 1
        assert "cleanup_disk.py" in " ".join(calls[0])
        assert result["archive"] is None
        assert result["cleanup"]["returncode"] == 0

    def test_skip_cleanup(self):
        from ops_maintenance import run_maintenance

        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            m = MagicMock()
            m.returncode = 0
            m.stdout = "{}"
            m.stderr = ""
            return m

        with patch("ops_maintenance.subprocess.run", side_effect=fake_run):
            result = run_maintenance(apply=False, skip_cleanup=True, root=Path("/tmp/proj"))

        assert len(calls) == 1
        assert "archive_low_score.py" in " ".join(calls[0])

    def test_nonzero_child_fails_overall(self):
        from ops_maintenance import run_maintenance

        def fake_run(cmd, **kwargs):
            m = MagicMock()
            if "archive" in " ".join(cmd):
                m.returncode = 2
                m.stdout = "boom"
                m.stderr = "err"
            else:
                m.returncode = 0
                m.stdout = "{}"
                m.stderr = ""
            return m

        with patch("ops_maintenance.subprocess.run", side_effect=fake_run):
            result = run_maintenance(apply=True, root=Path("/tmp/proj"))

        assert result["ok"] is False
        assert result["archive"]["returncode"] == 2
