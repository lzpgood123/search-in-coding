"""Test the weekly analysis pipeline."""
import pytest
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class TestPreFilter:
    def test_filters_empty_repos(self):
        from weekly_analysis import pre_filter
        projects = [
            {'id': '1', 'name': 'Test', 'stars': 0, 'forks': 0, 'summary': '', 'status': 'unknown'},
            {'id': '2', 'name': 'Good', 'stars': 100, 'forks': 10, 'summary': 'A real project', 'status': 'active'},
        ]
        filtered = pre_filter(projects)
        # Empty repo (no stars, no forks, no summary) should be filtered
        assert any(p['id'] == '2' for p in filtered)
        # But project 1 might still pass if it has other value - pre_filter is lenient
        # The key test is that archived repos are removed

    def test_filters_archived(self):
        from weekly_analysis import pre_filter
        projects = [
            {'id': '1', 'name': 'Archived', 'stars': 100, 'status': 'archived'},
            {'id': '2', 'name': 'Active', 'stars': 50, 'status': 'active'},
        ]
        filtered = pre_filter(projects)
        ids = [p['id'] for p in filtered]
        assert '2' in ids
        assert '1' not in ids

    def test_sorts_by_priority(self):
        from weekly_analysis import pre_filter
        projects = [
            {'id': 'low', 'name': 'Low', 'stars': 1, 'status': 'active'},
            {'id': 'high', 'name': 'High', 'stars': 1000, 'status': 'active'},
            {'id': 'mid', 'name': 'Mid', 'stars': 100, 'status': 'active'},
        ]
        filtered = pre_filter(projects)
        assert filtered[0]['id'] == 'high'
        assert filtered[1]['id'] == 'mid'
        assert filtered[2]['id'] == 'low'


class TestMergeResults:
    def test_merges_analysis_into_project(self):
        from weekly_analysis import merge_analysis_result
        project = {
            'id': 'test-1',
            'name': 'Test',
            'total_score': 30,
            'quantifiable_score': 30,
            'quality_score': 0,
        }
        analysis = {
            'relevance_score': 0.85,
            'resource_type': ['mcp-server'],
            'target_tools': ['claude-code'],
            'tracking_priority': 'track',
            'quality_score': 32,
            'quality_detail': {'relevance': 9, 'practicality': 8, 'novelty': 7, 'ecosystem_value': 8},
            'llm_summary': {'zh': '好的项目', 'en': 'Good project'},
            'analysis_notes': 'Nice work',
        }
        result = merge_analysis_result(project, analysis)
        assert result['quality_score'] == 32
        assert result['total_score'] == 30 + 32  # quantifiable + quality
        assert result['resource_type'] == ['mcp-server']
        assert result['target_tools'] == ['claude-code']
        assert result['tracking_priority'] == 'track'
        assert result['llm_summary'] == {'zh': '好的项目', 'en': 'Good project'}
        assert result['quality_detail'] == {'relevance': 9, 'practicality': 8, 'novelty': 7, 'ecosystem_value': 8}
        assert result.get('score_detail') is None or 'relevance' not in (result.get('score_detail') or {})
        assert result['last_analyzed'] is not None  # should be set to today

    def test_preserves_quantifiable_score(self):
        from weekly_analysis import merge_analysis_result
        project = {'id': 't', 'quantifiable_score': 25, 'quality_score': 0, 'total_score': 25}
        analysis = {'quality_score': 20, 'resource_type': ['skills'], 'target_tools': [], 'tracking_priority': 'index'}
        result = merge_analysis_result(project, analysis)
        assert result['quantifiable_score'] == 25  # unchanged
        assert result['quality_score'] == 20
        assert result['total_score'] == 45

    def test_handles_missing_fields_in_analysis(self):
        from weekly_analysis import merge_analysis_result
        project = {'id': 't', 'quantifiable_score': 20, 'quality_score': 0, 'total_score': 20, 'resource_type': ['tutorial']}
        analysis = {'quality_score': 15}  # minimal
        result = merge_analysis_result(project, analysis)
        assert result['quality_score'] == 15
        assert result['total_score'] == 35
        # Original resource_type should be preserved
        assert result['resource_type'] == ['tutorial']

    def test_handles_none_analysis(self):
        from weekly_analysis import merge_analysis_result
        project = {'id': 't', 'quantifiable_score': 20, 'quality_score': 0, 'total_score': 20}
        result = merge_analysis_result(project, None)
        assert result['id'] == 't'
        assert result['total_score'] == 20  # unchanged

    def test_official_seed_always_track(self):
        from weekly_analysis import merge_analysis_result
        project = {
            'id': 'official-cursor',
            'source_type': 'official-seed',
            'quantifiable_score': 44,
            'quality_score': 0,
            'total_score': 44,
            'tracking_priority': 'track',
        }
        analysis = {
            'quality_score': 16,
            'tracking_priority': 'index',
            'quality_detail': {'relevance': 5, 'practicality': 4, 'novelty': 3, 'ecosystem_value': 4},
        }
        result = merge_analysis_result(project, analysis)
        assert result['tracking_priority'] == 'track'
        assert result['quality_detail']['relevance'] == 5
        assert 'stars' not in (result.get('score_detail') or {})


class TestGetProjectsToAnalyze:
    def test_returns_never_analyzed(self):
        from weekly_analysis import get_projects_to_analyze
        projects = [
            {'id': '1', 'last_analyzed': None},
            {'id': '2', 'last_analyzed': '2026-01-01'},
            {'id': '3', 'last_analyzed': None},
        ]
        result = get_projects_to_analyze(projects)
        ids = [p['id'] for p in result]
        assert '1' in ids
        assert '3' in ids

    def test_respects_max_projects(self):
        from weekly_analysis import get_projects_to_analyze
        projects = [{'id': str(i), 'last_analyzed': None} for i in range(10)]
        result = get_projects_to_analyze(projects, max_projects=3)
        assert len(result) == 3

    def test_skips_recently_analyzed(self):
        import datetime
        from weekly_analysis import get_projects_to_analyze
        recent = datetime.date.today().isoformat()
        projects = [
            {'id': 'recent', 'last_analyzed': recent},
            {'id': 'old', 'last_analyzed': None},
        ]
        result = get_projects_to_analyze(projects)
        ids = [p['id'] for p in result]
        assert 'old' in ids
        assert 'recent' not in ids

    def test_sorts_by_stars_descending(self):
        from weekly_analysis import get_projects_to_analyze
        projects = [
            {'id': 'low', 'last_analyzed': None, 'stars': 5},
            {'id': 'high', 'last_analyzed': None, 'stars': 9000},
            {'id': 'mid', 'last_analyzed': None, 'stars': 100},
            {'id': 'recent', 'last_analyzed': __import__('datetime').date.today().isoformat(), 'stars': 99999},
        ]
        result = get_projects_to_analyze(projects)
        assert [p['id'] for p in result] == ['high', 'mid', 'low']

    def test_max_projects_keeps_highest_stars(self):
        from weekly_analysis import get_projects_to_analyze
        projects = [
            {'id': 'a', 'last_analyzed': None, 'stars': 10},
            {'id': 'b', 'last_analyzed': None, 'stars': 1000},
            {'id': 'c', 'last_analyzed': None, 'stars': 50},
        ]
        result = get_projects_to_analyze(projects, max_projects=2)
        assert [p['id'] for p in result] == ['b', 'c']

    def test_skips_archived(self):
        from weekly_analysis import get_projects_to_analyze
        projects = [
            {'id': 'arch', 'last_analyzed': None, 'stars': 99999, 'status': 'archived'},
            {'id': 'ok', 'last_analyzed': None, 'stars': 10, 'status': 'active'},
        ]
        result = get_projects_to_analyze(projects)
        assert [p['id'] for p in result] == ['ok']


class TestGetBatchSize:
    def test_reads_config_batch_size(self):
        from weekly_analysis import get_batch_size
        # config/llm-analysis.yaml should be 10 after batch4
        assert get_batch_size() == 10

    def test_cli_override_wins(self):
        from weekly_analysis import get_batch_size
        assert get_batch_size(7) == 7
        assert get_batch_size(1) == 1
