import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(rel):
    return json.loads((ROOT / rel).read_text())

def test_projects_have_i18n_and_auto_states():
    rows = load('data/projects.yaml')
    assert rows
    bad_states = {'reviewed','unreviewed','rejected','auto-reviewed'}
    for row in rows:
        assert row.get('id')
        assert {'zh','en'} <= set((row.get('i18n') or {}).keys())
        assert row.get('review_state') not in bad_states
        assert row.get('review_state') in {'auto-indexed','auto-curated','auto-rejected'}

def test_curated_and_rejected_states_are_consistent():
    for row in load('data/curated-projects.yaml'):
        assert row.get('review_state') == 'auto-curated'
        assert row.get('translation_state') in (None, 'rule-generated')
    for row in load('data/rejected-projects.yaml'):
        assert row.get('review_state') == 'auto-rejected'
