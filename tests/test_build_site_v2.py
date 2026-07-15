# tests/test_build_site_v2.py
"""Test build_site.py v2 features: slim JSON, detail JSON, sitemap, hash filenames."""
import pytest
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class TestBuildSiteV2:
    def test_slim_project_fields(self):
        """Slim projects.json should only contain table display fields."""
        from build_site import slim_project
        p = {
            'id': 'test', 'name': 'Test', 'url': 'https://github.com/o/r',
            'repo': 'o/r', 'source_type': 'github',
            'resource_type': ['mcp-server'], 'target_tools': ['claude-code'],
            'summary': 'A test', 'i18n': {'zh': {'name': 'Test', 'summary': 'A test'}, 'en': {}},
            'stars': 100, 'forks': 10, 'total_score': 35,
            'quantifiable_score': 35, 'quality_score': 0,
            'tracking_priority': 'pending',
            'last_updated': '2025-07-01', 'first_seen': '2025-07-01', 'last_seen': '2025-07-12',
            'license': 'MIT', 'languages': ['Python'],
            # These should NOT be in slim version:
            'score_detail': {'stars': 4, 'activity': 15},
            'llm_summary': {'zh': '...', 'en': '...'},
            'benchmark_ref': 'some-ref',
            'last_analyzed': '2025-07-10',
            'tags': ['ai'],
            'review_state': 'auto-indexed',
            'maturity': 'stable',
            'status': 'active',
        }
        slim = slim_project(p)
        assert 'id' in slim
        assert 'name' in slim
        assert 'total_score' in slim
        assert 'resource_type' in slim
        assert 'target_tools' in slim
        assert 'stars' in slim
        # Detail fields should NOT be in slim
        assert 'score_detail' not in slim
        assert 'llm_summary' in slim  # llm_summary added to SLIM_FIELDS for Chinese mode display
        assert 'benchmark_ref' not in slim
        assert 'last_analyzed' not in slim

    def test_detail_project_fields(self):
        """Detail JSON should contain all fields including LLM analysis."""
        from build_site import detail_project
        p = {
            'id': 'test', 'name': 'Test',
            'score_detail': {'stars': 4},
            'quality_detail': {'relevance': 9, 'practicality': 8, 'novelty': 7, 'ecosystem_value': 8},
            'llm_summary': {'zh': '好的', 'en': 'Good'},
            'benchmark_ref': 'ref-1',
            'last_analyzed': '2025-07-10',
            'tracking_priority': 'track',
            'quantifiable_score': 35,
            'quality_score': 0,
            'total_score': 35,
        }
        detail = detail_project(p)
        assert detail['id'] == 'test'
        assert 'score_detail' in detail
        assert 'quality_detail' in detail
        assert 'llm_summary' in detail
        assert 'benchmark_ref' in detail

    def test_hash_filename(self):
        from build_site import hash_filename
        h1 = hash_filename('app.js', 'content1')
        h2 = hash_filename('app.js', 'content2')
        assert h1 != h2
        assert h1.startswith('app.') and h1.endswith('.js')
        assert h2.startswith('app.') and h2.endswith('.js')

    def test_hash_filename_css(self):
        from build_site import hash_filename
        h = hash_filename('styles.css', 'body { color: red; }')
        assert h.startswith('styles.') and h.endswith('.css')
        assert len(h) > len('styles.css')  # should have hash inserted

    def test_generate_sitemap(self):
        from build_site import generate_sitemap
        sitemap = generate_sitemap([])
        assert '<?xml' in sitemap
        assert 'urlset' in sitemap
        assert 'https://coding.lzpgood.online/' in sitemap
        assert '<changefreq>daily</changefreq>' in sitemap
