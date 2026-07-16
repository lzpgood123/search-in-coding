#!/usr/bin/env python3
"""Seed-tools schema: validation, normalization, and active filtering.

This module manages the seed-tools state machine:
  status:        draft | active | disabled
  tool_kind:     open | closed
  onboard_state: pending | running | done | failed

Only `active` tools participate in collection / onboarding / filtering.
`closed` tools have no reliable public repo; they are tracked via ecosystem queries only.
"""
import sys
from pathlib import Path
from typing import Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, load_jsonish, save_jsonish

# ---- Constants ----

VALID_STATUSES = {'draft', 'active', 'disabled'}
VALID_TOOL_KINDS = {'open', 'closed'}
VALID_ONBOARD_STATES = {'pending', 'running', 'done', 'failed'}

REQUIRED_FIELDS = ('id', 'name', 'aliases')

SEED_TOOLS_PATH = 'data/seed-tools.yaml'


# ---- Functions ----

def normalize_tool_entry(entry: dict) -> dict:
    """Fill defaults for status / tool_kind / onboard_state.

    - status defaults to 'active' (for backward compat with existing tools)
    - tool_kind: 'open' if repo exists and is non-null, else 'closed'
    - onboard_state: defaults to 'pending' (new tools need onboarding)
    - Preserves all existing fields
    """
    result = dict(entry)  # shallow copy

    # tool_kind inference from repo
    repo = result.get('repo')
    if 'tool_kind' not in result:
        result['tool_kind'] = 'open' if repo else 'closed'

    # status default
    if 'status' not in result:
        result['status'] = 'active'

    # onboard_state default
    if 'onboard_state' not in result:
        result['onboard_state'] = 'pending'

    return result


def validate_tools(tools: list[dict]) -> list[str]:
    """Return a list of error strings; empty list means valid.

    Checks:
    - Required fields: id, name, aliases (non-empty)
    - Duplicate ids
    - Valid enum values for status, tool_kind, onboard_state
    """
    errors: list[str] = []
    seen_ids: set[str] = set()

    for i, tool in enumerate(tools):
        prefix = f"tool[{i}]" if 'id' not in tool else f"tool '{tool['id']}'"

        # Required fields
        for field in REQUIRED_FIELDS:
            val = tool.get(field)
            if field == 'aliases':
                if not val or not isinstance(val, list) or len(val) == 0:
                    errors.append(f"{prefix}: missing or empty '{field}'")
            elif not val:
                errors.append(f"{prefix}: missing '{field}'")

        # Duplicate id
        tid = tool.get('id')
        if tid:
            if tid in seen_ids:
                errors.append(f"{prefix}: duplicate id '{tid}'")
            else:
                seen_ids.add(tid)

        # Enum checks
        status = tool.get('status')
        if status and status not in VALID_STATUSES:
            errors.append(f"{prefix}: invalid status '{status}' (must be one of {VALID_STATUSES})")

        tool_kind = tool.get('tool_kind')
        if tool_kind and tool_kind not in VALID_TOOL_KINDS:
            errors.append(f"{prefix}: invalid tool_kind '{tool_kind}' (must be one of {VALID_TOOL_KINDS})")

        onboard_state = tool.get('onboard_state')
        if onboard_state and onboard_state not in VALID_ONBOARD_STATES:
            errors.append(f"{prefix}: invalid onboard_state '{onboard_state}' (must be one of {VALID_ONBOARD_STATES})")

    return errors


def iter_active_tools(tools: list[dict]) -> Iterator[dict]:
    """Yield only tools with status == 'active'.

    Tools with no status field are treated as active (backward compat).
    """
    for tool in tools:
        if tool.get('status', 'active') == 'active':
            yield tool


def load_seed_tools(normalize: bool = True) -> list[dict]:
    """Load seed-tools.yaml from disk.

    Args:
        normalize: If True, run normalize_tool_entry on each tool.
    """
    tools = load_jsonish(SEED_TOOLS_PATH)
    if not isinstance(tools, list):
        return []
    if normalize:
        tools = [normalize_tool_entry(t) for t in tools]
    return tools


def save_seed_tools(tools: list[dict]) -> None:
    """Save tools back to seed-tools.yaml."""
    save_jsonish(SEED_TOOLS_PATH, tools)


def update_onboard_state(tool_id: str, state: str, error: str | None = None) -> bool:
    """Update the onboard_state of a single tool in seed-tools.yaml.

    Returns True if the tool was found and updated.
    """
    if state not in VALID_ONBOARD_STATES:
        raise ValueError(f"Invalid onboard_state: {state}")

    tools = load_jsonish(SEED_TOOLS_PATH)
    if not isinstance(tools, list):
        return False

    found = False
    for tool in tools:
        if tool.get('id') == tool_id:
            tool['onboard_state'] = state
            if state == 'done':
                import datetime
                tool['onboarded_at'] = datetime.datetime.now().isoformat()
            if error:
                tool['onboard_error'] = error
            elif state == 'done':
                tool.pop('onboard_error', None)
            found = True
            break

    if found:
        save_seed_tools(tools)
    return found


def main():
    """CLI: validate and show seed-tools summary."""
    import argparse
    ap = argparse.ArgumentParser(description='Seed-tools schema validation')
    ap.add_argument('--validate', action='store_true', help='Validate seed-tools.yaml')
    ap.add_argument('--list-active', action='store_true', help='List active tool ids')
    ap.add_argument('--list-pending', action='store_true', help='List tools needing onboarding')
    args = ap.parse_args()

    tools = load_seed_tools(normalize=True)
    errors = validate_tools(tools)

    if errors:
        print("VALIDATION ERRORS:")
        for e in errors:
            print(f"  - {e}")
    else:
        print(f"OK: {len(tools)} tools, all valid")

    active = list(iter_active_tools(tools))
    print(f"Active: {len(active)}")
    pending = [t for t in active if t.get('onboard_state') in (None, 'pending', 'failed')]
    print(f"Needs onboarding: {len(pending)}")

    if args.list_active:
        for t in active:
            print(f"  {t['id']:30s} kind={t.get('tool_kind','?'):7s} onboard={t.get('onboard_state','?')}")

    if args.list_pending:
        for t in pending:
            print(f"  {t['id']:30s} onboard_state={t.get('onboard_state','?')}")

    return 1 if errors else 0


if __name__ == '__main__':
    import sys
    sys.exit(main() or 0)
