#!/usr/bin/env python3
"""Tests for seed_tools_schema.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from seed_tools_schema import (
    normalize_tool_entry,
    validate_tools,
    iter_active_tools,
    VALID_STATUSES,
    VALID_TOOL_KINDS,
    VALID_ONBOARD_STATES,
)


class TestNormalizeToolEntry:
    """normalize_tool_entry fills defaults and infers tool_kind."""

    def test_minimal_valid_entry(self):
        """Only id + name + aliases -> valid with defaults."""
        entry = {
            'id': 'my-tool',
            'name': 'My Tool',
            'aliases': ['My Tool', 'my-tool'],
        }
        result = normalize_tool_entry(entry)
        assert result['id'] == 'my-tool'
        assert result['name'] == 'My Tool'
        assert result['aliases'] == ['My Tool', 'my-tool']
        # repo missing -> tool_kind=closed
        assert result.get('repo') is None
        assert result['tool_kind'] == 'closed'
        # Default status for existing tools
        assert result['status'] == 'active'
        # Default onboard_state
        assert result['onboard_state'] == 'pending'

    def test_with_repo_gets_open(self):
        """Entry with repo -> tool_kind=open."""
        entry = {
            'id': 'claude-code',
            'name': 'Claude Code',
            'aliases': ['Claude Code'],
            'repo': 'anthropics/claude-code',
        }
        result = normalize_tool_entry(entry)
        assert result['tool_kind'] == 'open'
        assert result['repo'] == 'anthropics/claude-code'

    def test_repo_null_gets_closed(self):
        """Entry with repo=null -> tool_kind=closed."""
        entry = {
            'id': 'workbuddy-codebuddy',
            'name': 'WorkBuddy',
            'aliases': ['WorkBuddy'],
            'repo': None,
        }
        result = normalize_tool_entry(entry)
        assert result['tool_kind'] == 'closed'

    def test_preserves_existing_status(self):
        """Existing status is not overwritten."""
        entry = {
            'id': 'draft-tool',
            'name': 'Draft Tool',
            'aliases': ['Draft Tool'],
            'status': 'draft',
        }
        result = normalize_tool_entry(entry)
        assert result['status'] == 'draft'

    def test_preserves_existing_onboard_state(self):
        """Existing onboard_state is not overwritten."""
        entry = {
            'id': 'done-tool',
            'name': 'Done Tool',
            'aliases': ['Done Tool'],
            'onboard_state': 'done',
        }
        result = normalize_tool_entry(entry)
        assert result['onboard_state'] == 'done'

    def test_preserves_existing_tool_kind(self):
        """Explicit tool_kind is respected even if repo exists."""
        entry = {
            'id': 'special',
            'name': 'Special',
            'aliases': ['Special'],
            'repo': 'org/special',
            'tool_kind': 'closed',  # explicit override
        }
        result = normalize_tool_entry(entry)
        assert result['tool_kind'] == 'closed'

    def test_preserves_all_existing_fields(self):
        """All existing fields like vendor, extension_points etc are kept."""
        entry = {
            'id': 'claude-code',
            'name': 'Claude Code',
            'vendor': 'Anthropic',
            'aliases': ['Claude Code'],
            'repo': 'anthropics/claude-code',
            'extension_points': ['skills', 'hooks', 'mcp'],
            'config_files': ['CLAUDE.md'],
            'tracking_priority': 'high',
        }
        result = normalize_tool_entry(entry)
        assert result['vendor'] == 'Anthropic'
        assert result['extension_points'] == ['skills', 'hooks', 'mcp']
        assert result['config_files'] == ['CLAUDE.md']
        assert result['tracking_priority'] == 'high'


class TestValidateTools:
    """validate_tools checks required fields and returns errors."""

    def test_valid_list_passes(self):
        """A valid list of tools has no errors."""
        tools = [
            {'id': 'a', 'name': 'A', 'aliases': ['A'], 'status': 'active', 'tool_kind': 'open', 'onboard_state': 'done'},
            {'id': 'b', 'name': 'B', 'aliases': ['B'], 'status': 'active', 'tool_kind': 'closed', 'onboard_state': 'done'},
        ]
        errors = validate_tools(tools)
        assert errors == []

    def test_missing_id_is_error(self):
        """Tool without id is an error."""
        tools = [{'name': 'No ID', 'aliases': ['No ID']}]
        errors = validate_tools(tools)
        assert len(errors) == 1
        assert 'id' in errors[0].lower()

    def test_missing_name_is_error(self):
        """Tool without name is an error."""
        tools = [{'id': 'has-id', 'aliases': ['Has ID']}]
        errors = validate_tools(tools)
        assert len(errors) == 1
        assert 'name' in errors[0].lower()

    def test_missing_aliases_is_error(self):
        """Tool without aliases is an error."""
        tools = [{'id': 'has-id', 'name': 'Has Name'}]
        errors = validate_tools(tools)
        assert len(errors) == 1
        assert 'alias' in errors[0].lower()

    def test_empty_aliases_is_error(self):
        """Tool with empty aliases list is an error."""
        tools = [{'id': 'has-id', 'name': 'Has Name', 'aliases': []}]
        errors = validate_tools(tools)
        assert len(errors) == 1
        assert 'alias' in errors[0].lower()

    def test_duplicate_id_is_error(self):
        """Two tools with same id is an error."""
        tools = [
            {'id': 'dup', 'name': 'First', 'aliases': ['First']},
            {'id': 'dup', 'name': 'Second', 'aliases': ['Second']},
        ]
        errors = validate_tools(tools)
        assert len(errors) == 1
        assert 'duplicate' in errors[0].lower() or 'dup' in errors[0]

    def test_invalid_status_is_error(self):
        """Invalid status value is an error."""
        tools = [{'id': 'x', 'name': 'X', 'aliases': ['X'], 'status': 'bogus'}]
        errors = validate_tools(tools)
        assert len(errors) == 1
        assert 'status' in errors[0].lower()

    def test_invalid_tool_kind_is_error(self):
        """Invalid tool_kind value is an error."""
        tools = [{'id': 'x', 'name': 'X', 'aliases': ['X'], 'tool_kind': 'bogus'}]
        errors = validate_tools(tools)
        assert len(errors) == 1
        assert 'tool_kind' in errors[0].lower()

    def test_invalid_onboard_state_is_error(self):
        """Invalid onboard_state value is an error."""
        tools = [{'id': 'x', 'name': 'X', 'aliases': ['X'], 'onboard_state': 'bogus'}]
        errors = validate_tools(tools)
        assert len(errors) == 1
        assert 'onboard_state' in errors[0].lower()

    def test_normalized_list_passes(self):
        """List run through normalize_tool_entry should pass validation."""
        raw = [
            {'id': 'a', 'name': 'A', 'aliases': ['A']},
            {'id': 'b', 'name': 'B', 'aliases': ['B'], 'repo': 'org/b'},
        ]
        normalized = [normalize_tool_entry(t) for t in raw]
        errors = validate_tools(normalized)
        assert errors == []


class TestIterActiveTools:
    """iter_active_tools yields only active tools."""

    def test_filters_draft_and_disabled(self):
        """Only active tools are yielded."""
        tools = [
            {'id': 'active1', 'name': 'A1', 'aliases': ['A1'], 'status': 'active'},
            {'id': 'draft1', 'name': 'D1', 'aliases': ['D1'], 'status': 'draft'},
            {'id': 'disabled1', 'name': 'Dis1', 'aliases': ['Dis1'], 'status': 'disabled'},
            {'id': 'active2', 'name': 'A2', 'aliases': ['A2'], 'status': 'active'},
        ]
        active = list(iter_active_tools(tools))
        ids = [t['id'] for t in active]
        assert ids == ['active1', 'active2']

    def test_missing_status_defaults_active(self):
        """Tool with no status field is treated as active."""
        tools = [
            {'id': 'no-status', 'name': 'NS', 'aliases': ['NS']},
        ]
        # normalize first (as pipeline does)
        normalized = [normalize_tool_entry(t) for t in tools]
        active = list(iter_active_tools(normalized))
        assert len(active) == 1
        assert active[0]['id'] == 'no-status'

    def test_empty_list(self):
        """Empty list yields nothing."""
        assert list(iter_active_tools([])) == []
