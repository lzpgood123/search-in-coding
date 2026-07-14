"""Tests for scripts/enrich_projects.py resilience."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import enrich_projects as ep  # noqa: E402


def _timeout_error(cmd: str = "gh api ...") -> subprocess.TimeoutExpired:
    return subprocess.TimeoutExpired(cmd=cmd, timeout=60)


def test_fetch_readme_timeout_returns_empty_not_raise():
    with patch.object(ep, "run", side_effect=_timeout_error()):
        assert ep.fetch_readme("geelen/mcp-remote") == ""


def test_fetch_readme_other_exception_returns_empty():
    with patch.object(ep, "run", side_effect=OSError("network down")):
        assert ep.fetch_readme("owner/repo") == ""


def test_enrich_readme_only_timeout_marks_checked_and_continues():
    project = {"repo": "geelen/mcp-remote", "name": "mcp-remote"}
    with patch.object(ep, "fetch_readme", side_effect=_timeout_error()):
        # Even if fetch_readme itself raises (pre-fix), enrich_readme_only
        # must not propagate; post-fix fetch_readme returns "".
        pass
    with patch.object(ep, "fetch_readme", return_value=""):
        out, changed, note = ep.enrich_readme_only(dict(project))
        assert changed is True
        assert out.get("readme_checked") is True
        assert out.get("readme_preview") == ""
        assert note in ("empty-readme", "ok", "timeout", "error")


def test_enrich_readme_only_when_fetch_raises_does_not_crash():
    """If lower layer still raises TimeoutExpired, enrich_readme_only swallows it."""
    project = {"repo": "geelen/mcp-remote", "name": "mcp-remote"}
    with patch.object(ep, "fetch_readme", side_effect=_timeout_error()):
        out, changed, note = ep.enrich_readme_only(dict(project))
    assert changed is True
    assert out.get("readme_checked") is True
    assert note in ("timeout", "error", "empty-readme")
    # Should not re-fetch forever after a hard failure
    assert out.get("readme_checked") is True


def test_enrich_one_future_path_survives_timeout_via_enrich_readme_only():
    project = {"repo": "geelen/mcp-remote", "name": "mcp-remote"}
    with patch.object(ep, "fetch_readme", side_effect=_timeout_error()):
        out, changed, note = ep.enrich_one(dict(project), readme_only=True)
    assert changed is True
    assert out.get("readme_checked") is True


def test_main_as_completed_swallows_worker_exception(tmp_path, monkeypatch):
    """main() must not die if a future raises unexpectedly."""
    projects = [
        {"repo": "a/b", "name": "a", "stars": 10},
        {"repo": "c/d", "name": "c", "stars": 5},
    ]
    monkeypatch.setattr(ep, "load_jsonish", lambda rel: projects)
    saves = []

    def fake_save(rel, data):
        saves.append(list(data))

    monkeypatch.setattr(ep, "save_jsonish", fake_save)

    def boom(project, readme_only=False):
        raise subprocess.TimeoutExpired(cmd="gh", timeout=1)

    monkeypatch.setattr(ep, "enrich_one", boom)
    monkeypatch.setattr(
        sys,
        "argv",
        ["enrich_projects.py", "--readme-only", "--batch-size", "2", "--sleep", "0"],
    )
    # Should complete without raising
    ep.main()
    assert saves, "should still save progress at end"
