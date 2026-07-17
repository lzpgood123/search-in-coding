"""Tests for normalize.py field mapping and resource_type classification.

Covers batch A3 (field mapping) and A4 (resource_type misclassification).
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

def load_module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ============================================================
# A3: github_record() field mapping tests
# ============================================================

def test_github_record_stars_from_stargazerCount():
    """stars should be extracted from stargazerCount (repo view API)."""
    normalize = load_module('normalize')
    item = {
        'nameWithOwner': 'test/repo',
        'url': 'https://github.com/test/repo',
        'description': 'test',
        'stargazerCount': 1234,
        'forkCount': 10,
    }
    rec = normalize.github_record(item, [])
    assert rec['stars'] == 1234, f"stars={rec['stars']}"


def test_github_record_stars_from_stargazersCount():
    """stars should fall back to stargazersCount (search API)."""
    normalize = load_module('normalize')
    item = {
        'fullName': 'test/search-repo',
        'url': 'https://github.com/test/search-repo',
        'description': 'test',
        'stargazersCount': 100,
    }
    rec = normalize.github_record(item, [])
    assert rec['stars'] == 100, f"stars={rec['stars']}"


def test_github_record_forks_from_forkCount():
    """forks should be extracted from forkCount."""
    normalize = load_module('normalize')
    item = {
        'nameWithOwner': 'test/repo',
        'url': 'https://github.com/test/repo',
        'stargazerCount': 100,
        'forkCount': 56,
    }
    rec = normalize.github_record(item, [])
    assert rec['forks'] == 56, f"forks={rec['forks']}"


def test_github_record_license_from_spdxId():
    """license should be extracted from licenseInfo.spdxId."""
    normalize = load_module('normalize')
    item = {
        'nameWithOwner': 'test/repo',
        'url': 'https://github.com/test/repo',
        'stargazerCount': 100,
        'forkCount': 10,
        'licenseInfo': {'spdxId': 'MIT'},
    }
    rec = normalize.github_record(item, [])
    assert rec['license'] == 'MIT', f"license={rec['license']}"


def test_github_record_license_null_when_no_license():
    """license should be None when licenseInfo is null."""
    normalize = load_module('normalize')
    item = {
        'nameWithOwner': 'test/repo',
        'url': 'https://github.com/test/repo',
        'stargazerCount': 100,
        'forkCount': 10,
        'licenseInfo': None,
    }
    rec = normalize.github_record(item, [])
    assert rec['license'] is None, f"license={rec['license']}"


def test_github_record_license_noassertion_becomes_null():
    """NOASSERTION license should become None."""
    normalize = load_module('normalize')
    item = {
        'nameWithOwner': 'test/repo',
        'url': 'https://github.com/test/repo',
        'stargazerCount': 100,
        'forkCount': 10,
        'licenseInfo': {'spdxId': 'NOASSERTION'},
    }
    rec = normalize.github_record(item, [])
    assert rec['license'] is None, f"license={rec['license']}"


def test_github_record_license_from_key_fallback():
    """When spdxId is None, license should fall back to 'key' field (gh repo view behavior)."""
    normalize = load_module('normalize')
    item = {
        'nameWithOwner': 'test/repo',
        'url': 'https://github.com/test/repo',
        'stargazerCount': 100,
        'forkCount': 10,
        'licenseInfo': {'key': 'mit', 'name': 'MIT License', 'spdxId': None},
    }
    rec = normalize.github_record(item, [])
    assert rec['license'] == 'mit', f"license={rec['license']}"


def test_github_record_languages_from_primaryLanguage():
    """languages should be extracted from primaryLanguage.name."""
    normalize = load_module('normalize')
    item = {
        'nameWithOwner': 'test/repo',
        'url': 'https://github.com/test/repo',
        'stargazerCount': 100,
        'forkCount': 10,
        'primaryLanguage': {'name': 'Python'},
    }
    rec = normalize.github_record(item, [])
    assert rec['languages'] == ['Python'], f"languages={rec['languages']}"


def test_github_record_languages_from_language_string():
    """languages should fall back to 'language' string field (search API)."""
    normalize = load_module('normalize')
    item = {
        'fullName': 'test/search-repo',
        'url': 'https://github.com/test/search-repo',
        'stargazersCount': 100,
        'language': 'JavaScript',
    }
    rec = normalize.github_record(item, [])
    assert rec['languages'] == ['JavaScript'], f"languages={rec['languages']}"


def test_github_record_languages_empty_when_null():
    """languages should be empty list when primaryLanguage is null."""
    normalize = load_module('normalize')
    item = {
        'nameWithOwner': 'test/repo',
        'url': 'https://github.com/test/repo',
        'stargazerCount': 100,
        'forkCount': 10,
        'primaryLanguage': None,
    }
    rec = normalize.github_record(item, [])
    assert rec['languages'] == [], f"languages={rec['languages']}"


def test_github_record_topics_from_repositoryTopics():
    """topics should be extracted from repositoryTopics list."""
    normalize = load_module('normalize')
    item = {
        'nameWithOwner': 'test/repo',
        'url': 'https://github.com/test/repo',
        'stargazerCount': 100,
        'forkCount': 10,
        'repositoryTopics': [{'name': 'claude'}, {'name': 'skill'}],
    }
    rec = normalize.github_record(item, [])
    assert rec['topics'] == ['claude', 'skill'], f"topics={rec['topics']}"


def test_github_record_topics_empty_when_missing():
    """topics should be empty list when repositoryTopics is missing."""
    normalize = load_module('normalize')
    item = {
        'nameWithOwner': 'test/repo',
        'url': 'https://github.com/test/repo',
        'stargazerCount': 100,
        'forkCount': 10,
    }
    rec = normalize.github_record(item, [])
    assert rec['topics'] == [], f"topics={rec['topics']}"


def test_github_record_readme_preview():
    """readme_preview should be first 500 chars of readme."""
    normalize = load_module('normalize')
    item = {
        'nameWithOwner': 'test/repo',
        'url': 'https://github.com/test/repo',
        'stargazerCount': 100,
        'forkCount': 10,
        'readme': '# Test\n\nThis is a test readme.' + 'x' * 600,
    }
    rec = normalize.github_record(item, [])
    assert len(rec['readme_preview']) == 500, f"readme_preview len={len(rec['readme_preview'])}"


def test_github_record_readme_preview_empty_when_missing():
    """readme_preview should be empty string when readme is missing."""
    normalize = load_module('normalize')
    item = {
        'nameWithOwner': 'test/repo',
        'url': 'https://github.com/test/repo',
        'stargazerCount': 100,
        'forkCount': 10,
    }
    rec = normalize.github_record(item, [])
    assert rec['readme_preview'] == '', f"readme_preview={rec['readme_preview']!r}"


# ============================================================
# A4: resource_types_for() classification tests
# ============================================================

def test_skill_not_misclassified_as_tutorial_caveman():
    """'Claude Code skill' should be classified as 'skills', not just 'tutorial'."""
    normalize = load_module('normalize')
    types = normalize.resource_types_for('caveman Claude Code skill that cuts 65% of tokens')
    assert 'skills' in types, f"caveman types={types}"


def test_skill_not_misclassified_as_tutorial_humanizer():
    normalize = load_module('normalize')
    types = normalize.resource_types_for('humanizer Claude Code skill that removes signs of AI-generated writing')
    assert 'skills' in types, f"humanizer types={types}"


def test_skill_not_misclassified_as_tutorial_book_to_skill():
    normalize = load_module('normalize')
    types = normalize.resource_types_for('Turn any technical book PDF into a Claude Code skill')
    assert 'skills' in types, f"book-to-skill types={types}"


def test_extension_detected():
    """'extension' keyword should be classified as 'extension' type."""
    normalize = load_module('normalize')
    types = normalize.resource_types_for('Conductor is a Gemini CLI extension that allows you to specify')
    assert 'extension' in types, f"conductor types={types}"


def test_tutorial_still_detected():
    """Tutorial keywords should still be detected when no concrete type matches."""
    normalize = load_module('normalize')
    types = normalize.resource_types_for('Best practices and case study for newcomers')
    assert 'tutorial' in types, f"tutorial types={types}"
    assert types == ['tutorial'] or 'tutorial' in types


def test_mcp_server_detected():
    normalize = load_module('normalize')
    types = normalize.resource_types_for('Claude Code as one-shot MCP server')
    assert 'mcp-server' in types, f"mcp types={types}"


def test_rules_detected():
    normalize = load_module('normalize')
    types = normalize.resource_types_for('Curated list of awesome Cursor Rules .mdc files')
    assert 'rules' in types, f"rules types={types}"


def test_agent_framework_detected():
    normalize = load_module('normalize')
    types = normalize.resource_types_for('Multi-agent orchestration framework')
    assert 'agent-framework' in types, f"framework types={types}"


def test_rules_not_false_match_overrules():
    """'overrules' should not match 'rules' keyword (substring issue)."""
    normalize = load_module('normalize')
    assert 'rules' not in normalize.resource_types_for('overrules nothing')


def test_mcp_not_false_match_campus():
    normalize = load_module('normalize')
    assert 'mcp-server' not in normalize.resource_types_for('campus demo unrelated')


def test_default_tutorial_when_nothing_matches():
    """When nothing matches, default to ['tutorial']."""
    normalize = load_module('normalize')
    types = normalize.resource_types_for('some random project about coding')
    assert types == ['tutorial'], f"default types={types}"


# ============================================================
# Batch 3: topics mapping, keyword expansion, empty tools, safe merge
# ============================================================

def test_topics_map_to_mcp_server():
    normalize = load_module('normalize')
    types = normalize.resource_types_for('some random repo', topics=['mcp-server', 'python'])
    assert 'mcp-server' in types
    assert types != ['tutorial']


def test_topics_map_to_skills():
    normalize = load_module('normalize')
    types = normalize.resource_types_for('utility helpers', topics=['claude-skills', 'agent-skills'])
    assert 'skills' in types


def test_topics_map_to_rules():
    normalize = load_module('normalize')
    types = normalize.resource_types_for('config pack', topics=['cursor-rules', 'cursorrules'])
    assert 'rules' in types


def test_topics_map_to_agent_framework():
    normalize = load_module('normalize')
    types = normalize.resource_types_for('orchestration stuff', topics=['multi-agent', 'agent-framework'])
    assert 'agent-framework' in types


def test_topics_map_to_cli_tool():
    normalize = load_module('normalize')
    types = normalize.resource_types_for('dev utilities', topics=['cli-tool', 'command-line'])
    assert 'cli-tool' in types


def test_topics_map_to_tutorial():
    normalize = load_module('normalize')
    types = normalize.resource_types_for('learning materials', topics=['awesome-list', 'guide'])
    assert 'tutorial' in types


def test_ai_topics_do_not_fallback_to_cli_tool():
    """AI-related topics alone must NOT force cli-tool; still tutorial if no type match."""
    normalize = load_module('normalize')
    types = normalize.resource_types_for(
        'random helper library about widgets',
        topics=['ai', 'llm', 'claude', 'openai', 'agents'],
    )
    assert 'cli-tool' not in types, f"AI topics must not become cli-tool: {types}"
    assert types == ['tutorial'], f"expected tutorial fallback, got {types}"


def test_keyword_expansion_mcp_gateway():
    normalize = load_module('normalize')
    types = normalize.resource_types_for('An MCP gateway for tool routing')
    assert 'mcp-server' in types


def test_keyword_expansion_agent_skills_library():
    normalize = load_module('normalize')
    types = normalize.resource_types_for('A skill library and prompt library for coding agents')
    assert 'skills' in types


def test_keyword_expansion_coding_agent_framework():
    normalize = load_module('normalize')
    types = normalize.resource_types_for('coding agent runtime and agent platform SDK')
    assert 'agent-framework' in types


def test_keyword_expansion_devtool_assistant():
    normalize = load_module('normalize')
    types = normalize.resource_types_for('AI code assistant and developer tool for completion')
    assert 'cli-tool' in types


def test_concrete_type_does_not_also_force_tutorial_tag():
    """When a concrete type matches, do not also append tutorial."""
    normalize = load_module('normalize')
    types = normalize.resource_types_for('MCP server guide and tutorial for beginners')
    assert 'mcp-server' in types
    assert 'tutorial' not in types


def test_target_tools_from_topics():
    normalize = load_module('normalize')
    tools = [
        {'id': 'claude-code', 'name': 'Claude Code', 'aliases': ['claude-code']},
        {'id': 'cursor', 'name': 'Cursor', 'aliases': ['cursor']},
    ]
    ids = normalize.target_tools_for('generic description', tools, topics=['claude-code', 'cursor'])
    assert 'claude-code' in ids
    assert 'cursor' in ids
    assert 'general-ai-coding' not in ids


def test_target_tools_general_when_ai_topics_no_match():
    normalize = load_module('normalize')
    tools = [{'id': 'claude-code', 'name': 'Claude Code', 'aliases': ['claude-code']}]
    ids = normalize.target_tools_for('unrelated widgets', tools, topics=['ai-agents', 'llm'])
    assert ids == ['general-ai-coding']


def test_target_tools_empty_when_no_match_no_ai_topics():
    normalize = load_module('normalize')
    tools = [{'id': 'claude-code', 'name': 'Claude Code', 'aliases': ['claude-code']}]
    ids = normalize.target_tools_for('postgresql backup utility', tools, topics=['database', 'sql'])
    assert ids == []


def test_target_tools_empty_when_no_topics_no_match():
    normalize = load_module('normalize')
    tools = [{'id': 'claude-code', 'name': 'Claude Code', 'aliases': ['claude-code']}]
    ids = normalize.target_tools_for('postgresql backup utility', tools, topics=[])
    assert ids == []


def test_github_record_passes_topics_into_classification():
    normalize = load_module('normalize')
    item = {
        'nameWithOwner': 'test/mcp-thing',
        'url': 'https://github.com/test/mcp-thing',
        'description': 'a helpful package',
        'stargazerCount': 10,
        'forkCount': 1,
        'repositoryTopics': [{'name': 'mcp-server'}, {'name': 'model-context-protocol'}],
    }
    rec = normalize.github_record(item, [])
    assert 'mcp-server' in rec['resource_type']


def test_safe_merge_preserves_llm_fields():
    normalize = load_module('normalize')
    existing = {
        'id': 'github-test-repo',
        'url': 'https://github.com/test/repo',
        'name': 'test/repo',
        'source_type': 'github',
        'resource_type': ['tutorial'],
        'target_tools': ['general-ai-coding'],
        'summary': 'old summary with translation',
        'i18n': {'zh': {'name': 'test', 'summary': '中文摘要'}, 'en': {'name': 'test', 'summary': 'old'}},
        'quality_score': 28,
        'quality_detail': {'relevance': 0.9},
        'tracking_priority': 'track',
        'last_analyzed': '2026-07-10',
        'benchmark_ref': 'official-hermes-agent',
        'readme_preview': 'Existing readme preview content here',
        'topics': ['ai'],
        'stars': 100,
        'quantifiable_score': 40,
        'total_score': 68,
        'score_detail': {'stars': 20},
        'review_state': 'auto-curated',
        'first_seen': '2026-01-01',
    }
    incoming = {
        'id': 'github-test-repo',
        'url': 'https://github.com/test/repo',
        'name': 'test/repo',
        'source_type': 'github',
        'resource_type': ['cli-tool'],
        'target_tools': ['claude-code'],
        'summary': 'new raw summary',
        'i18n': {'zh': {'name': 'test', 'summary': 'new raw summary'}, 'en': {'name': 'test', 'summary': 'new raw summary'}},
        'quality_score': 0,
        'quality_detail': {},
        'tracking_priority': 'pending',
        'last_analyzed': None,
        'benchmark_ref': None,
        'readme_preview': '',
        'topics': ['cli'],
        'stars': 150,
        'quantifiable_score': 0,
        'total_score': 0,
        'score_detail': {},
        'review_state': 'auto-indexed',
        'first_seen': None,
    }
    merged = normalize.safe_merge_record(existing, incoming, today='2026-07-15')
    assert merged['quality_score'] == 28
    assert merged['quality_detail'] == {'relevance': 0.9}
    assert merged['tracking_priority'] == 'track'
    assert merged['last_analyzed'] == '2026-07-10'
    assert merged['benchmark_ref'] == 'official-hermes-agent'
    assert merged['readme_preview'] == 'Existing readme preview content here'
    assert merged['stars'] == 150
    assert merged['review_state'] == 'auto-curated'
    assert merged['first_seen'] == '2026-01-01'
    assert '中文摘要' in (merged.get('i18n') or {}).get('zh', {}).get('summary', '')


def test_safe_merge_official_seed_protection():
    normalize = load_module('normalize')
    existing = {
        'id': 'official-claude-code',
        'url': 'https://github.com/anthropics/claude-code',
        'name': 'Claude Code',
        'source_type': 'official-seed',
        'resource_type': ['cli-tool', 'agent-framework'],
        'target_tools': ['claude-code'],
        'tracking_priority': 'track',
        'quality_score': 37,
        'last_analyzed': '2026-07-10',
        'benchmark_ref': 'official-hermes-agent',
        'stars': 10,
        'summary': 'Official Claude Code',
        'i18n': {'zh': {'name': 'Claude Code', 'summary': '官方'}, 'en': {'name': 'Claude Code', 'summary': 'Official'}},
    }
    incoming = {
        'id': 'github-anthropics-claude-code',
        'url': 'https://github.com/anthropics/claude-code',
        'name': 'anthropics/claude-code',
        'source_type': 'github',
        'resource_type': ['tutorial'],
        'target_tools': ['general-ai-coding'],
        'tracking_priority': 'pending',
        'quality_score': 0,
        'last_analyzed': None,
        'benchmark_ref': None,
        'stars': 999,
        'summary': 'raw',
        'i18n': {},
        'topics': ['cli'],
    }
    merged = normalize.safe_merge_record(existing, incoming, today='2026-07-15')
    assert merged['source_type'] == 'official-seed'
    assert merged['tracking_priority'] == 'track'
    assert merged['name'] == 'Claude Code'
    assert merged['quality_score'] == 37
    assert merged['last_analyzed'] == '2026-07-10'
    assert merged['stars'] == 999


def test_reclassify_project_does_not_read_readme_preview():
    """normalize classification must ignore readme_preview content."""
    normalize = load_module('normalize')
    tools = [{'id': 'claude-code', 'name': 'Claude Code', 'aliases': ['claude-code']}]
    project = {
        'name': 'acme/widgets',
        'summary': 'a simple widget pack',
        'topics': [],
        'readme_preview': 'This is an MCP server with model context protocol tools and Claude Code skills',
        'source_type': 'github',
    }
    out = normalize.reclassify_project(project, tools)
    assert out['resource_type'] == ['tutorial']
    assert 'mcp-server' not in out['resource_type']


# ============================================================
# target_tools topic substring matching guards (2026-07-17)
# ============================================================

def _agent_alias_tools():
    """Minimal seed-like tools that previously false-matched topic 'agent'."""
    return [
        {'id': 'trae', 'name': 'Trae / Trae Work', 'aliases': ['Trae', 'Trae Agent', 'Trae SOLO', 'Trae Work']},
        {'id': 'hermes-agent', 'name': 'Hermes Agent', 'aliases': ['Hermes Agent', 'Nous Hermes', 'Hermes coding agent']},
        {'id': 'replit', 'name': 'Replit', 'aliases': ['Replit', 'Replit Agent', 'Ghostwriter']},
        {'id': 'claude-code', 'name': 'Claude Code', 'aliases': ['claude-code', 'Claude Code']},
        {'id': 'cursor', 'name': 'Cursor', 'aliases': ['cursor', 'Cursor']},
        {'id': 'ai-short', 'name': 'AI', 'aliases': ['ai']},
    ]


def test_topic_agent_does_not_match_trae_hermes_replit():
    """topic 'agent' must NOT match aliases like 'Trae Agent' (tn in al bug)."""
    normalize = load_module('normalize')
    tools = _agent_alias_tools()
    ids = normalize.target_tools_for(
        'Page Agent browser automation',
        tools,
        topics=['agent', 'browser', 'automation'],
    )
    assert 'trae' not in ids
    assert 'hermes-agent' not in ids
    assert 'replit' not in ids
    assert ids == ['general-ai-coding']


def test_topic_exact_match_still_works():
    """Exact topic == alias/id match is always allowed regardless of length."""
    normalize = load_module('normalize')
    tools = _agent_alias_tools()
    ids = normalize.target_tools_for('generic', tools, topics=['claude-code'])
    assert 'claude-code' in ids
    assert 'general-ai-coding' not in ids


def test_alias_substring_of_topic_requires_len_ge_5():
    """alias in topic allowed only when both alias and topic are >= 5 chars."""
    normalize = load_module('normalize')
    tools = _agent_alias_tools()
    ids = normalize.target_tools_for('generic', tools, topics=['cursor-extension'])
    assert 'cursor' in ids


def test_short_alias_substring_blocked():
    """Short alias (<5) must not substring-match longer topics."""
    normalize = load_module('normalize')
    tools = _agent_alias_tools()
    ids = normalize.target_tools_for('unrelated widgets', tools, topics=['ai-agents', 'llm'])
    assert 'ai-short' not in ids
    assert ids == ['general-ai-coding']


def test_exact_short_alias_still_matches():
    """Exact match al == tn still works even if alias is short."""
    normalize = load_module('normalize')
    tools = [{'id': 'ai-short', 'name': 'AI', 'aliases': ['ai']}]
    ids = normalize.target_tools_for('generic', tools, topics=['ai'])
    assert ids == ['ai-short']
