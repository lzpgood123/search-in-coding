"""Test data migration from old schema to new 100-point schema."""
import pytest
import sys
from pathlib import Path

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from migrate_data import migrate_project, should_remove_project


class TestShouldRemoveProject:
    def test_removes_fallback_web(self):
        p = {'source_type': 'fallback-web'}
        assert should_remove_project(p) is True

    def test_removes_exa(self):
        p = {'source_type': 'exa'}
        assert should_remove_project(p) is True

    def test_keeps_github(self):
        p = {'source_type': 'github'}
        assert should_remove_project(p) is False

    def test_keeps_official_seed(self):
        p = {'source_type': 'official-seed'}
        assert should_remove_project(p) is False


class TestMigrateProject:
    def test_removes_old_score_fields(self):
        p = {
            'id': 'test',
            'name': 'Test',
            'source_type': 'github',
            'score': {'ecosystem_value': 3, 'activity': 2},
            'score_reason': {'base': 18, 'source_weight': 2},
            'total_score': 20,
            'category': ['mcp-acp-a2a'],
            'record_kind': 'ecosystem-project',
            'ranking_scope': 'ecosystem',
            'source_quality': 'verified',
            'concepts': [],
            'integration_surfaces': [],
            'why_it_matters': 'test',
            'notes': '',
        }
        result = migrate_project(p)
        assert 'score' not in result  # old 6-dim score removed
        assert 'score_reason' not in result
        assert 'category' not in result  # replaced by resource_type
        assert 'record_kind' not in result
        assert 'ranking_scope' not in result
        assert 'source_quality' not in result
        assert 'concepts' not in result
        assert 'integration_surfaces' not in result
        assert 'why_it_matters' not in result
        assert 'notes' not in result

    def test_adds_new_fields(self):
        p = {
            'id': 'test',
            'name': 'Test',
            'source_type': 'github',
            'category': ['mcp-acp-a2a', 'skills-prompts'],
            'target_tools': ['claude-code'],
            'stars': 500,
            'forks': 10,
        }
        result = migrate_project(p)
        assert 'resource_type' in result
        assert 'quantifiable_score' in result
        assert result['quantifiable_score'] >= 0
        assert result['quantifiable_score'] <= 60
        assert 'quality_score' in result
        assert result['quality_score'] == 0  # placeholder until LLM analysis
        assert 'total_score' in result
        assert result['total_score'] == result['quantifiable_score']  # = quantifiable + 0
        assert 'tracking_priority' in result
        assert result['tracking_priority'] == 'pending'
        assert 'last_analyzed' in result
        assert result['last_analyzed'] is None
        assert 'benchmark_ref' in result
        assert result['benchmark_ref'] is None

    def test_migrates_category_to_resource_type(self):
        p = {
            'id': 'test',
            'name': 'Test MCP Server',
            'source_type': 'github',
            'category': ['mcp-acp-a2a'],
            'target_tools': ['claude-code'],
        }
        result = migrate_project(p)
        assert 'mcp-server' in result['resource_type']

    def test_migrates_multiple_categories(self):
        p = {
            'id': 'test',
            'name': 'Claude Skills Collection',
            'source_type': 'github',
            'category': ['skills-prompts', 'mcp-acp-a2a'],
            'target_tools': ['claude-code'],
        }
        result = migrate_project(p)
        assert 'skills' in result['resource_type']
        assert 'mcp-server' in result['resource_type']

    def test_official_tool_preserved(self):
        p = {
            'id': 'claude-code',
            'name': 'Claude Code',
            'source_type': 'official-seed',
            'category': ['official-tool'],
            'target_tools': ['claude-code'],
            'stars': 50000,
        }
        result = migrate_project(p)
        assert result['tracking_priority'] == 'track'
        assert result['source_type'] == 'official-seed'

    def test_preserves_retained_fields(self):
        p = {
            'id': 'test',
            'name': 'Test',
            'url': 'https://github.com/owner/repo',
            'repo': 'owner/repo',
            'source_type': 'github',
            'summary': 'A test project',
            'i18n': {'zh': {'name': 'Test', 'summary': 'A test project'}, 'en': {'name': 'Test', 'summary': 'A test project'}},
            'status': 'active',
            'stars': 1000,
            'forks': 50,
            'last_updated': '2025-06-01T00:00:00Z',
            'first_seen': '2025-06-01',
            'last_seen': '2025-07-12',
            'maturity': 'stable',
            'languages': ['Python'],
            'tags': ['ai'],
            'target_tools': ['claude-code'],
            'review_state': 'auto-indexed',
            'license': 'MIT',
        }
        result = migrate_project(p)
        for field in ['id', 'name', 'url', 'repo', 'source_type', 'summary', 'i18n',
                       'status', 'stars', 'forks', 'last_updated', 'first_seen',
                       'last_seen', 'maturity', 'languages', 'tags', 'target_tools',
                       'review_state', 'license']:
            assert field in result, f'{field} should be preserved'
