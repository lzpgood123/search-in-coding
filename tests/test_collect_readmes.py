"""Tests for collect_readmes.py."""
import base64
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


def test_fetch_and_store_readme_writes_file_and_flag(tmp_path):
    collect = load_module('collect_readmes')
    project = {
        'id': 'github-demo-skills',
        'repo': 'demo/skills',
        'tracking_priority': 'track',
        'has_readme_full': False,
    }
    fake_content = base64.b64encode(b'# Hello full README').decode('ascii')

    class FakeResult:
        returncode = 0
        stdout = fake_content + '\n'
        stderr = ''

    with patch.object(collect, 'run', return_value=FakeResult()):
        with patch.object(collect, 'ROOT', tmp_path):
            pid, changed, note = collect.fetch_and_store_readme(project)
    assert changed is True
    assert note == 'ok'
    assert project['has_readme_full'] is True
    path = tmp_path / 'data' / 'readmes' / 'github-demo-skills.md'
    assert path.exists()
    assert path.read_text(encoding='utf-8') == '# Hello full README'
    assert len(project.get('readme_preview') or '') <= 2000
    assert project['readme_preview'].startswith('# Hello')


def test_select_projects_skips_already_collected():
    collect = load_module('collect_readmes')
    projects = [
        {'id': 'a', 'repo': 'a/a', 'tracking_priority': 'track', 'has_readme_full': True},
        {'id': 'b', 'repo': 'b/b', 'tracking_priority': 'track', 'has_readme_full': False},
        {'id': 'c', 'repo': 'c/c', 'tracking_priority': 'index', 'has_readme_full': False},
        {'id': 'd', 'repo': '', 'tracking_priority': 'track', 'has_readme_full': False},
    ]
    selected = collect.select_projects(projects, priority='track', force=False)
    assert [p['id'] for p in selected] == ['b']
