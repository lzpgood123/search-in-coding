"""Test cleanup_disk.py logic."""
import pytest
import sys
import tempfile
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class TestParseDate:
    def test_parses_valid_date(self):
        from cleanup_disk import parse_date
        d = parse_date('2026-07-15')
        assert d == datetime.date(2026, 7, 15)

    def test_returns_none_for_invalid(self):
        from cleanup_disk import parse_date
        assert parse_date('not-a-date') is None
        assert parse_date('2026-13-45') is None
        assert parse_date('') is None


class TestFindExpiredDirs:
    def test_finds_old_raw_dirs(self, tmp_path):
        from cleanup_disk import find_expired_dirs
        # Create old and recent dirs
        old = tmp_path / '2026-06-01'
        recent = tmp_path / '2026-07-14'
        old.mkdir()
        recent.mkdir()
        today = datetime.date(2026, 7, 15)
        expired = find_expired_dirs(tmp_path, keep_days=30, today=today)
        names = [d.name for d in expired]
        assert '2026-06-01' in names
        assert '2026-07-14' not in names

    def test_skips_non_date_dirs(self, tmp_path):
        from cleanup_disk import find_expired_dirs
        (tmp_path / 'not-a-date').mkdir()
        (tmp_path / '2026-06-01').mkdir()
        today = datetime.date(2026, 7, 15)
        expired = find_expired_dirs(tmp_path, keep_days=30, today=today)
        names = [d.name for d in expired]
        assert '2026-06-01' in names
        assert 'not-a-date' not in names


class TestFindExpiredFiles:
    def test_finds_old_snapshot_files(self, tmp_path):
        from cleanup_disk import find_expired_files
        # Create old and recent JSON files
        old = tmp_path / '2026-04-01.json'
        recent = tmp_path / '2026-07-14.json'
        old.write_text('{}')
        recent.write_text('{}')
        today = datetime.date(2026, 7, 15)
        expired = find_expired_files(tmp_path, keep_days=90, today=today)
        names = [f.name for f in expired]
        assert '2026-04-01.json' in names
        assert '2026-07-14.json' not in names

    def test_skips_non_date_files(self, tmp_path):
        from cleanup_disk import find_expired_files
        (tmp_path / 'config.json').write_text('{}')
        (tmp_path / '2026-04-01.json').write_text('{}')
        today = datetime.date(2026, 7, 15)
        expired = find_expired_files(tmp_path, keep_days=90, today=today)
        names = [f.name for f in expired]
        assert '2026-04-01.json' in names
        assert 'config.json' not in names
