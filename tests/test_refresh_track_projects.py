"""Test track project refresh logic."""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class TestSelectProjectsToRefresh:
    def test_selects_track_projects_only(self):
        from refresh_track_projects import select_projects_to_refresh
        projects = [
            {'id': '1', 'tracking_priority': 'track', 'repo': 'a/b', 'last_seen': '2026-07-10'},
            {'id': '2', 'tracking_priority': 'reject', 'repo': 'c/d', 'last_seen': '2026-07-10'},
            {'id': '3', 'tracking_priority': 'pending', 'repo': 'e/f', 'last_seen': '2026-07-10'},
        ]
        selected = select_projects_to_refresh(projects, batch_size=10)
        ids = [p['id'] for p in selected]
        assert '1' in ids
        assert '2' not in ids
        assert '3' not in ids

    def test_skips_official_seed(self):
        from refresh_track_projects import select_projects_to_refresh
        projects = [
            {'id': '1', 'tracking_priority': 'track', 'source_type': 'official-seed', 'repo': 'a/b'},
            {'id': '2', 'tracking_priority': 'track', 'source_type': 'github', 'repo': 'c/d'},
        ]
        selected = select_projects_to_refresh(projects, batch_size=10)
        ids = [p['id'] for p in selected]
        assert '2' in ids
        assert '1' not in ids  # official-seed 跳过

    def test_skips_projects_without_repo(self):
        from refresh_track_projects import select_projects_to_refresh
        projects = [
            {'id': '1', 'tracking_priority': 'track', 'repo': 'a/b', 'last_seen': '2026-07-10'},
            {'id': '2', 'tracking_priority': 'track', 'repo': None, 'last_seen': '2026-07-10'},
            {'id': '3', 'tracking_priority': 'track', 'last_seen': '2026-07-10'},  # no repo key
        ]
        selected = select_projects_to_refresh(projects, batch_size=10)
        ids = [p['id'] for p in selected]
        assert '1' in ids
        assert '2' not in ids
        assert '3' not in ids

    def test_sorts_by_last_seen_oldest_first(self):
        from refresh_track_projects import select_projects_to_refresh
        projects = [
            {'id': 'new', 'tracking_priority': 'track', 'repo': 'a/b', 'last_seen': '2026-07-15'},
            {'id': 'old', 'tracking_priority': 'track', 'repo': 'c/d', 'last_seen': '2026-07-01'},
            {'id': 'mid', 'tracking_priority': 'track', 'repo': 'e/f', 'last_seen': '2026-07-10'},
        ]
        selected = select_projects_to_refresh(projects, batch_size=10)
        ids = [p['id'] for p in selected]
        assert ids == ['old', 'mid', 'new']  # oldest first

    def test_respects_batch_size(self):
        from refresh_track_projects import select_projects_to_refresh
        projects = [
            {'id': str(i), 'tracking_priority': 'track', 'repo': f'a/b{i}', 'last_seen': '2026-07-01'}
            for i in range(50)
        ]
        selected = select_projects_to_refresh(projects, batch_size=10)
        assert len(selected) == 10


class TestMergeRefreshedData:
    def test_updates_stars_and_forks(self):
        from refresh_track_projects import merge_refreshed_data
        existing = {
            'id': '1', 'name': 'test', 'repo': 'a/b',
            'stars': 100, 'forks': 10,
            'quality_score': 30, 'tracking_priority': 'track',
            'llm_summary': 'important',
        }
        refreshed = {
            'stargazerCount': 150, 'forkCount': 20,
            'updatedAt': '2026-07-15T00:00:00Z',
        }
        merged = merge_refreshed_data(existing, refreshed)
        assert merged['stars'] == 150
        assert merged['forks'] == 20
        assert merged['last_updated'] == '2026-07-15T00:00:00Z'
        # LLM 字段必须保留
        assert merged['quality_score'] == 30
        assert merged['tracking_priority'] == 'track'
        assert merged['llm_summary'] == 'important'

    def test_preserves_summary_if_empty_in_refresh(self):
        from refresh_track_projects import merge_refreshed_data
        existing = {'id': '1', 'summary': 'old summary', 'repo': 'a/b'}
        refreshed = {'description': '', 'stargazerCount': 100}
        merged = merge_refreshed_data(existing, refreshed)
        assert merged['summary'] == 'old summary'
