"""Tests for retarget_tools.py — only target_tools may change."""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_apply_retarget_only_updates_target_tools():
    retarget = load_module('retarget_tools')
    project = {
        'id': 'github-anthropics-skills',
        'name': 'anthropics/skills',
        'target_tools': ['zed'],
        'quality_score': 35,
        'resource_type': ['skills'],
        'tracking_priority': 'track',
        'llm_summary': {'zh': 'x', 'en': 'y'},
        'total_score': 80,
    }
    result = {
        'target_tools': ['claude-code'],
        'reason': 'official anthropic skills',
    }
    out = retarget.apply_retarget_result(project, result, valid_ids={'claude-code', 'zed', 'cursor'})
    assert out['target_tools'] == ['claude-code']
    assert out['quality_score'] == 35
    assert out['resource_type'] == ['skills']
    assert out['tracking_priority'] == 'track'
    assert out['llm_summary'] == {'zh': 'x', 'en': 'y'}
    assert out['total_score'] == 80


def test_apply_retarget_keeps_original_on_empty_or_invalid():
    retarget = load_module('retarget_tools')
    project = {
        'id': 'p1',
        'target_tools': ['cursor'],
        'quality_score': 20,
    }
    out = retarget.apply_retarget_result(project, None, valid_ids={'cursor'})
    assert out['target_tools'] == ['cursor']
    out2 = retarget.apply_retarget_result(project, {'target_tools': []}, valid_ids={'cursor'})
    # empty array is valid (no specific tools) — but plan says empty keeps original?
    # Spec risk: "若 LLM 返回空则保留原值"
    assert out2['target_tools'] == ['cursor']


def test_build_retarget_prompt_lists_tools_and_readme():
    retarget = load_module('retarget_tools')
    tools = [
        {'id': 'claude-code', 'name': 'Claude Code', 'aliases': ['Claude Code', 'claude', 'cc']},
        {'id': 'cursor', 'name': 'Cursor', 'aliases': ['Cursor']},
    ]
    project = {
        'id': 'github-x',
        'name': 'x/y',
        'topics': ['skills'],
        'target_tools': ['zed'],
        'readme_preview': 'short',
    }
    readme_dir = ROOT / 'data' / 'readmes'
    readme_dir.mkdir(parents=True, exist_ok=True)
    path = readme_dir / 'github-x.md'
    path.write_text('FULL BODY FOR RETARGET', encoding='utf-8')
    try:
        prompt = retarget.build_retarget_prompt(project, tools)
        assert 'claude-code' in prompt
        assert 'Cursor' in prompt
        assert 'FULL BODY FOR RETARGET' in prompt
        assert 'x/y' in prompt
    finally:
        path.unlink(missing_ok=True)


def test_filter_valid_tool_ids():
    retarget = load_module('retarget_tools')
    valid = {'claude-code', 'cursor', 'general-ai-coding'}
    assert retarget.filter_valid_tool_ids(['claude-code', 'nope', 'cursor'], valid) == [
        'claude-code', 'cursor'
    ]
    assert retarget.filter_valid_tool_ids(['general-ai-coding'], valid) == ['general-ai-coding']
