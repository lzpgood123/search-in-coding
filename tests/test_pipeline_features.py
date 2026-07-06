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

def test_normalize_short_tokens_do_not_false_match():
    normalize = load_module('normalize')
    assert 'mcp-acp-a2a' not in normalize.categories_for('campus demo unrelated')
    assert 'rules-instructions' not in normalize.categories_for('overrules nothing')
    assert 'mcp-acp-a2a' in normalize.categories_for('Claude Code MCP server integration')

def test_finalize_weak_record_helper():
    finalize = load_module('finalize_data')
    ranking = finalize.DEFAULT_RANKING
    assert finalize.is_weak_record({'total_score': 1}, ranking)
    assert finalize.is_weak_record({'total_score': 50, 'source_type': 'fallback-web'}, ranking)
    assert not finalize.is_weak_record({'total_score': 50, 'source_type': 'github', 'target_tools': ['claude-code'], 'source_quality': 'verified'}, ranking)
