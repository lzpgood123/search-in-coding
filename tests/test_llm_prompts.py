"""Tests for llm_prompts dynamic tools list + full README loading."""
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


def test_project_analysis_prompt_includes_active_tools():
    llm_prompts = load_module('llm_prompts')
    active_tools = [
        {'id': 'claude-code', 'name': 'Claude Code', 'aliases': ['Claude Code', 'claude']},
        {'id': 'cursor', 'name': 'Cursor', 'aliases': ['Cursor']},
        {'id': 'zed', 'name': 'Zed', 'aliases': ['Zed']},
    ]
    project = {
        'id': 'github-demo-proj',
        'name': 'demo/proj',
        'summary': 'demo',
        'url': 'https://github.com/demo/proj',
        'stars': 1,
        'forks': 0,
        'languages': ['Python'],
        'license': 'MIT',
        'last_updated': '2026-07-01',
        'target_tools': [],
        'topics': ['ai'],
        'readme_preview': 'preview only',
    }
    prompt = llm_prompts.project_analysis_prompt(project, active_tools=active_tools)
    assert 'claude-code' in prompt
    assert 'cursor' in prompt
    assert 'zed' in prompt
    assert 'hermes-agent' not in prompt or 'active_tools'  # dynamic list, not only hardcoded fallback


def test_project_analysis_prompt_reads_full_readme_file(tmp_path, monkeypatch):
    llm_prompts = load_module('llm_prompts')
    # write full readme under project data/readmes
    readme_dir = ROOT / 'data' / 'readmes'
    readme_dir.mkdir(parents=True, exist_ok=True)
    pid = 'github-test-full-readme-prompt'
    full = 'FULL README CONTENT ' + ('Y' * 800)
    path = readme_dir / f'{pid}.md'
    path.write_text(full, encoding='utf-8')
    try:
        project = {
            'id': pid,
            'name': 'test/full-readme',
            'summary': 's',
            'url': 'https://github.com/test/full-readme',
            'stars': 0,
            'forks': 0,
            'languages': [],
            'license': None,
            'last_updated': None,
            'target_tools': [],
            'topics': [],
            'readme_preview': 'preview short',
        }
        prompt = llm_prompts.project_analysis_prompt(project, active_tools=[
            {'id': 'claude-code', 'name': 'Claude Code', 'aliases': []},
        ])
        assert 'FULL README CONTENT' in prompt
        assert 'YYYY' in prompt
        assert 'first 500 chars' not in prompt
    finally:
        path.unlink(missing_ok=True)


def test_project_analysis_prompt_truncates_readme_over_50000():
    llm_prompts = load_module('llm_prompts')
    pid = 'github-test-huge-readme-prompt'
    readme_dir = ROOT / 'data' / 'readmes'
    readme_dir.mkdir(parents=True, exist_ok=True)
    path = readme_dir / f'{pid}.md'
    path.write_text('A' * 60000, encoding='utf-8')
    try:
        project = {
            'id': pid,
            'name': 'test/huge',
            'summary': 's',
            'url': 'https://github.com/test/huge',
            'stars': 0,
            'forks': 0,
            'languages': [],
            'license': None,
            'last_updated': None,
            'target_tools': [],
            'topics': [],
            'readme_preview': 'preview',
        }
        prompt = llm_prompts.project_analysis_prompt(project)
        # should not embed all 60k
        assert 'A' * 50001 not in prompt
        assert 'A' * 1000 in prompt
    finally:
        path.unlink(missing_ok=True)
