#!/usr/bin/env python3
"""Normalize raw collector outputs and reclassify existing projects.

Batch 3 rules:
- resource_types_for(text, topics): keywords + topics mapping; default tutorial
- NEVER map bare AI topics → cli-tool
- target_tools_for may return [] when no tool match and no AI topic signal
- normalize does NOT read readme_preview for classification
- safe_merge preserves LLM fields and official-seed protection
"""
from __future__ import annotations

import argparse
import copy
import datetime
import json
import re

from common import ROOT, load_jsonish, save_jsonish, slug

# Resource type rules: ordered by priority (earlier = higher priority)
RESOURCE_TYPE_RULES = {
    'mcp-server': [
        'mcp server', 'model context protocol', 'mcp tool', 'mcp integration',
        'mcp gateway', 'mcp hub', 'mcp client', 'mcp-', ' mcp',
        # bare "mcp" handled carefully via word-ish phrases above + topics
    ],
    'skills': [
        'claude code skill', 'claude skill', 'agent skill', 'coding skill',
        'skill pack', 'skill collection', 'skills &', 'skills and',
        'prompt pack', 'slash command', 'custom command',
        'skill that', 'skills for', 'skill to', 'skill set',
        'claude code skills', 'agent skills', 'skill library', 'prompt library',
        'command library', 'skills framework', 'skill framework',
        'agentic skills', 'skills for claude', 'claude-skills',
        ' skill', 'skills', '/skill', 'skill.md', 'skills.md',
        'agent skill', 'skills collection', 'skill marketplace',
    ],
    'extension': [
        'extension', 'plugin', 'addon', 'add-on', 'vscode extension',
        'vs code extension', 'ide extension', 'chrome extension',
        'jetbrains', 'vscode', 'vs code',
    ],
    'rules': [
        'agents.md', 'claude.md', 'cursor rules', '.cursorrules',
        'ruleset', 'instruction file', 'rules file', 'rules for',
        'cursor rule', 'rules .mdc', 'rules mdc',
        'coding rules', 'ai rules', 'behavioral guidance', 'system prompt',
        'system prompts', 'cursorrules', 'prompt engineering tutorial',
        'prompt pack',
    ],
    'agent-framework': [
        'agent framework', 'multi-agent', 'subagent',
        'agent orchestration', 'agentic framework', 'agent system',
        'agent desktop', 'autonomous agent',
        'agent runtime', 'agent platform', 'agent sdk',
        'coding agent', 'code agent', 'agent harness', 'agent toolkit',
        'agentic workflow', 'multi agent', 'swarm of agents',
        'ai agent framework', 'agentic coding framework',
        'ai agent', 'ai agents', 'agentic', 'autonomous agents',
        'manage agents', 'agent team', 'agents at work', 'agent-native',
        'multi-agent', 'agent swarm', 'agent orchestr',
        'ai agency', 'agents framework', 'for ai agents',
        'ai-driven development', 'agent-managed', 'agent harness',
        'meta-prompting', 'spec-driven development',
    ],
    'cli-tool': [
        'cli ', 'cli tool', 'command line', 'terminal',
        'codebase index', 'repo map', 'repository map',
        'semantic search', 'codebase indexing', 'code search',
        'cli extension', 'developer tool', 'devtool', 'dev tool',
        'code assistant', 'ai assistant', 'code completion',
        'terminal agent', 'coding cli', 'cli for',
        'coding assistant', 'ai coding assistant', 'developer-tools',
        'devtools', 'dev-tools', 'code intelligence', 'code graph',
        'pre-indexed', 'autocomplete', 'copilot', 'proxy api',
        'cli-anything', 'coding infrastructure', 'router for',
    ],
    'tutorial': [
        'tutorial', 'best practice', 'case study',
        'benchmark', 'evaluation', 'eval harness', 'leaderboard',
        'awesome list', 'curated list', 'learning path', 'course for',
        'from zero to', 'for beginners', 'getting started guide',
        'interactive tutorial', 'lessons to', 'from scratch',
        'awesome-', 'integration list',
    ],
}

# topics → resource_type (exact topic name, lowercased)
TOPIC_RESOURCE_MAP = {
    'mcp-server': 'mcp-server',
    'model-context-protocol': 'mcp-server',
    'mcp': 'mcp-server',
    'mcp-servers': 'mcp-server',
    'claude-skills': 'skills',
    'agent-skills': 'skills',
    'skills': 'skills',
    'claude-code-skills': 'skills',
    'codex-skills': 'skills',
    'skill': 'skills',
    'cursor-rules': 'rules',
    'cursorrules': 'rules',
    'rules': 'rules',
    'agent-framework': 'agent-framework',
    'multi-agent': 'agent-framework',
    'multiagent': 'agent-framework',
    'agentic-framework': 'agent-framework',
    'ai-agents-framework': 'agent-framework',
    'ai-agent': 'agent-framework',
    'ai-agents': 'agent-framework',
    'agentic-ai': 'agent-framework',
    'agentic-workflow': 'agent-framework',
    'ai-runtime': 'agent-framework',
    'code-execution': 'agent-framework',
    'langchain': 'agent-framework',
    'autonomous-agents': 'agent-framework',
    'cli': 'cli-tool',
    'cli-tool': 'cli-tool',
    'command-line': 'cli-tool',
    'terminal': 'cli-tool',
    'developer-tools': 'cli-tool',
    'devtools': 'cli-tool',
    'code-intelligence': 'cli-tool',
    'tutorial': 'tutorial',
    'awesome-list': 'tutorial',
    'awesome': 'tutorial',
    'guide': 'tutorial',
    'vscode-extension': 'extension',
    'browser-extension': 'extension',
    'chrome-extension': 'extension',
    'plugin': 'extension',
    'prompt-engineering': 'rules',
}

# topics that signal AI-coding relevance for general-ai-coding fallback
AI_TOPIC_SIGNALS = {
    'ai', 'llm', 'llms', 'agent', 'agents', 'ai-agent', 'ai-agents',
    'ai-coding', 'ai-tools', 'ai-assistant', 'coding-agent', 'coding-agents',
    'agentic-ai', 'agentic', 'generative-ai', 'chatgpt', 'openai', 'anthropic',
    'claude', 'claude-code', 'gemini', 'codex', 'cursor', 'opencode',
    'vibe-coding', 'prompt-engineering', 'rag', 'mcp', 'llm-agent',
    'artificial-intelligence', 'machine-learning', 'deep-learning',
    'openclaw', 'hermes', 'goose', 'devin', 'copilot',
}

CONCRETE_RESOURCE_ORDER = [
    'mcp-server', 'skills', 'extension', 'rules', 'agent-framework', 'cli-tool',
]

LLM_PRESERVE_FIELDS = (
    'quality_score',
    'quality_detail',
    'tracking_priority',
    'last_analyzed',
    'benchmark_ref',
    'llm_summary',
)

GITHUB_REFRESH_FIELDS = (
    'stars', 'forks', 'license', 'topics', 'languages',
    'last_updated', 'status', 'readme_preview', 'name', 'repo',
)

ZH_RE = re.compile(r'[\u4e00-\u9fff]')


def i18n_fields(name, summary):
    name = name or ''
    summary = summary or ''
    return {'zh': {'name': name, 'summary': summary}, 'en': {'name': name, 'summary': summary}}


def has_any(text, phrases):
    low = text.lower()
    return any(p.lower() in low for p in phrases)


def _normalize_topics(topics):
    if not topics:
        return []
    out = []
    for t in topics:
        if isinstance(t, dict):
            name = t.get('name')
        else:
            name = t
        if name:
            out.append(str(name).lower().strip())
    return out


def _has_ai_topic_signal(topics_norm):
    for t in topics_norm:
        if t in AI_TOPIC_SIGNALS:
            return True
        # loose contains for compound topics
        if any(sig in t for sig in ('agent', 'llm', 'claude', 'openai', 'coding', 'mcp', 'gpt')):
            return True
    return False


def resource_types_for(text, topics=None):
    """Determine resource_type tags from project text + topics.

    Phase 1: keyword match on name/description text (priority order).
    Phase 1.5: topics exact mapping.
    Fallback: ['tutorial'] when nothing matches.
    Does NOT read readme_preview. Does NOT map bare AI topics → cli-tool.
    """
    low = (text or '').lower()
    types = []

    # Phase 1: concrete resource types from keywords
    for rt in CONCRETE_RESOURCE_ORDER:
        phrases = RESOURCE_TYPE_RULES.get(rt, [])
        if has_any(low, phrases):
            types.append(rt)
    # bare "mcp" as whole-ish token (avoid campus)
    if 'mcp-server' not in types:
        if re.search(r'(?<![a-z])mcp(?![a-z])', low):
            types.append('mcp-server')

    # Phase 1.5: topics mapping
    topics_norm = _normalize_topics(topics)
    for t in topics_norm:
        mapped = TOPIC_RESOURCE_MAP.get(t)
        if mapped and mapped not in types:
            # concrete first; tutorial from topics only if no concrete yet
            if mapped == 'tutorial':
                continue
            types.append(mapped)

    if types:
        # concrete matches win; do not also force tutorial tag
        return types

    # tutorial keywords or tutorial-ish topics only when no concrete type
    if has_any(low, RESOURCE_TYPE_RULES.get('tutorial', [])):
        return ['tutorial']
    for t in topics_norm:
        if TOPIC_RESOURCE_MAP.get(t) == 'tutorial':
            return ['tutorial']

    # Explicit: AI topics alone still default to tutorial (NOT cli-tool)
    return ['tutorial']


def target_tools_for(text, tools, topics=None):
    """Match seed-tool aliases in text and topics.

    - alias match → tool ids
    - else if AI/coding topic signals → ['general-ai-coding']
    - else → []

    Topic matching rules (2026-07-17 fix):
    - exact match al == tn: always ok (no length floor)
    - alias is substring of topic (al in tn): only if len(al) >= 5 and len(tn) >= 5
    - NEVER match topic as substring of alias (tn in al) — short topics like
      "agent" were falsely hitting "Trae Agent" / "Hermes Agent" / "Replit Agent"
    """
    low = (text or '').lower()
    topics_norm = _normalize_topics(topics)
    ids = []
    for t in tools or []:
        aliases = list(t.get('aliases') or []) + [t.get('name', ''), t.get('id', '')]
        matched = False
        for a in aliases:
            if not a:
                continue
            al = a.lower()
            # free-text contains full alias phrase (description/name path)
            if al in low:
                matched = True
                break
            # per-topic matching with length guards (no topic_blob: short
            # aliases like "ai" would false-match joined "ai-agents llm")
            for tn in topics_norm:
                if al == tn:
                    matched = True
                    break
                if len(al) >= 5 and len(tn) >= 5 and al in tn:
                    matched = True
                    break
                # intentionally NO: tn in al
            if matched:
                break
        if matched and t.get('id') and t['id'] not in ids:
            ids.append(t['id'])

    if ids:
        return ids
    if _has_ai_topic_signal(topics_norm):
        return ['general-ai-coding']
    # text-level weak AI signal when topics empty
    if not topics_norm and has_any(low, [
        'ai coding', 'coding agent', 'llm', 'claude', 'cursor', 'codex',
        'openai', 'anthropic', 'agentic', 'mcp server', 'ai agent',
    ]):
        return ['general-ai-coding']
    return []


def reclassify_project(project, tools):
    """Recompute resource_type/target_tools from name+summary+topics only."""
    if not project:
        return project
    if project.get('source_type') == 'official-seed':
        project['tracking_priority'] = 'track'
        return project

    name = project.get('name') or ''
    summary = project.get('summary') or ''
    # IMPORTANT: do not use readme_preview
    text = f'{name} {summary}'
    topics = project.get('topics') or []
    project['resource_type'] = resource_types_for(text, topics)
    project['target_tools'] = target_tools_for(text, tools, topics)
    return project


def _has_analysis_trace(rec: dict) -> bool:
    if not rec:
        return False
    if rec.get('last_analyzed'):
        return True
    if rec.get('llm_summary'):
        return True
    qs = rec.get('quality_score')
    try:
        if qs is not None and float(qs) > 0:
            return True
    except (TypeError, ValueError):
        pass
    qd = rec.get('quality_detail')
    if isinstance(qd, dict) and any(v for v in qd.values()):
        return True
    return False


def safe_merge_record(existing, incoming, today=None, skip_existing=False):
    """Merge incoming GitHub-normalized record into existing without dropping LLM fields."""
    day = today or datetime.date.today().isoformat()

    if existing is None:
        rec = copy.deepcopy(incoming)
        rec['first_seen'] = rec.get('first_seen') or day
        rec['last_seen'] = day
        rec.setdefault('tracking_priority', 'pending')
        rec.setdefault('quality_score', 0)
        return rec

    if skip_existing:
        return existing

    out = copy.deepcopy(existing)
    inc = incoming or {}

    # official-seed protection
    if out.get('source_type') == 'official-seed':
        for k in GITHUB_REFRESH_FIELDS:
            if k == 'name':
                continue
            v = inc.get(k)
            if v is not None and v != '' and v != []:
                out[k] = v
        if not out.get('repo') and inc.get('repo'):
            out['repo'] = inc['repo']
        out['last_seen'] = day
        out['source_type'] = 'official-seed'
        out['tracking_priority'] = 'track'
        return out

    # refresh GitHub quantifiable fields
    for k in GITHUB_REFRESH_FIELDS:
        v = inc.get(k)
        if v is None or v == '' or v == []:
            continue
        out[k] = v

    # Always refresh classification from incoming when present
    if inc.get('resource_type'):
        out['resource_type'] = inc['resource_type']
    if 'target_tools' in inc and inc.get('target_tools') is not None:
        out['target_tools'] = inc['target_tools']

    # summary: only fill if old empty
    if not (out.get('summary') or '').strip():
        if inc.get('summary'):
            out['summary'] = inc['summary']

    # i18n: keep existing non-empty better i18n
    old_i18n = out.get('i18n') or {}
    new_i18n = inc.get('i18n') or {}
    if not old_i18n:
        out['i18n'] = new_i18n
    else:
        def _summ(block, lang):
            return ((block or {}).get(lang) or {}).get('summary') or ''
        keep = bool(_summ(old_i18n, 'zh').strip() or _summ(old_i18n, 'en').strip())
        if not keep and new_i18n:
            out['i18n'] = new_i18n

    # preserve LLM / human fields
    for k in LLM_PRESERVE_FIELDS:
        if k not in existing:
            continue
        if k == 'tracking_priority' and existing.get(k):
            out[k] = existing[k]
        elif k in ('quality_score', 'quality_detail', 'last_analyzed', 'benchmark_ref', 'llm_summary'):
            if existing.get(k) not in (None, '', {}, 0, 0.0) or _has_analysis_trace(existing):
                out[k] = existing.get(k)

    # review_state: keep non-default if analysis trace
    if _has_analysis_trace(existing) or (
        existing.get('review_state') and existing.get('review_state') != 'auto-indexed'
    ):
        out['review_state'] = existing.get('review_state')

    # preserve quantifiable score fields until score.py re-runs
    for k in ('quantifiable_score', 'total_score', 'score_detail'):
        if existing.get(k) not in (None, '', {}):
            out[k] = existing.get(k)

    out['first_seen'] = existing.get('first_seen') or day
    out['last_seen'] = day

    if existing.get('source_type') == 'official-seed':
        out['source_type'] = 'official-seed'

    return out


def github_record(it, tools):
    fn = it.get('fullName') or it.get('nameWithOwner')
    url = it.get('url') or (f'https://github.com/{fn}' if fn else None)
    name = fn or it.get('name') or url
    if not url or not name:
        return None
    desc = it.get('description') or ''
    text = f'{name} {desc}'

    stars = it.get('stargazerCount')
    if stars is None:
        stars = it.get('stargazersCount')

    summary = desc[:240] or name

    license_info = it.get('licenseInfo')
    if isinstance(license_info, dict):
        license_id = license_info.get('spdxId')
        if not license_id:
            license_id = license_info.get('key')
        license_val = None if license_id in ('NOASSERTION', None, '', 'none') else license_id
    else:
        license_val = None

    forks = it.get('forkCount')
    if forks is None:
        forks = it.get('forks')

    primary_lang = it.get('primaryLanguage')
    if isinstance(primary_lang, dict):
        lang_name = primary_lang.get('name')
    else:
        lang_name = it.get('language')
    languages = [lang_name] if lang_name else []

    topics_raw = it.get('repositoryTopics') or []
    if isinstance(topics_raw, list):
        topics = [t.get('name') if isinstance(t, dict) else t for t in topics_raw]
        topics = [t for t in topics if t]
    else:
        topics = []

    readme = it.get('readme') or ''
    readme_preview = readme[:500] if readme else ''

    return {
        'id': slug('github-' + name),
        'name': name,
        'url': url,
        'repo': fn,
        'source_type': 'github',
        'resource_type': resource_types_for(text, topics),
        'target_tools': target_tools_for(text, tools, topics),
        'summary': summary,
        'i18n': i18n_fields(name, summary),
        'status': 'archived' if it.get('isArchived') else 'unknown',
        'license': license_val,
        'stars': stars,
        'forks': forks,
        'last_updated': it.get('updatedAt') or it.get('pushedAt'),
        'first_seen': None,
        'last_seen': None,
        'maturity': 'unknown',
        'languages': languages,
        'topics': topics,
        'readme_preview': readme_preview,
        'tags': [],
        'review_state': 'auto-indexed',
        'quantifiable_score': 0,
        'quality_score': 0,
        'total_score': 0,
        'score_detail': {},
        'tracking_priority': 'pending',
        'last_analyzed': None,
        'benchmark_ref': None,
    }


def from_github():
    tools = load_jsonish('data/seed-tools.yaml')
    by_url = {}

    raw_root = ROOT / 'data/raw/github'
    if not raw_root.exists():
        return []

    for d in sorted(raw_root.glob('*')):
        for p in sorted(d.glob('*.json')):
            if p.name.endswith('-error.json'):
                continue
            data = json.loads(p.read_text(encoding='utf-8'))
            items = data if isinstance(data, list) else data.get('results', [])
            if p.name == 'repo-details.json':
                items = data
            for it in items:
                rec = github_record(it, tools)
                if not rec:
                    continue
                url = rec.get('url')
                existing = by_url.get(url)
                if existing:
                    for k, v in rec.items():
                        if v is not None and (existing.get(k) is None or existing.get(k) == []):
                            existing[k] = v
                    if len(rec.get('resource_type', [])) > len(existing.get('resource_type', [])):
                        existing['resource_type'] = rec['resource_type']
                    # re-run classification with merged topics
                    text = f"{existing.get('name','')} {existing.get('summary','')}"
                    existing['resource_type'] = resource_types_for(text, existing.get('topics') or [])
                    existing['target_tools'] = target_tools_for(text, tools, existing.get('topics') or [])
                else:
                    by_url[url] = rec
    return list(by_url.values())


def main():
    ap = argparse.ArgumentParser(description='Normalize raw collector outputs into data/projects.yaml')
    ap.add_argument('--source', choices=['all', 'github'], default='all')
    ap.add_argument('--skip-raw', action='store_true', help='Only reclassify existing projects.yaml')
    ap.parse_known_args()
    args, _ = ap.parse_known_args()

    tools = load_jsonish('data/seed-tools.yaml')
    existing = load_jsonish('data/projects.yaml') if (ROOT / 'data/projects.yaml').exists() else []
    if not isinstance(existing, list):
        existing = []

    by = {}
    for r in existing:
        key = r.get('url') or r.get('id')
        if key:
            by[key] = r

    recs = [] if args.skip_raw else from_github()
    now = datetime.date.today().isoformat()
    for r in recs:
        key = r.get('url') or r['id']
        prev = by.get(key)
        by[key] = safe_merge_record(prev, r, today=now)

    # Reclassify all projects in place (name+summary+topics only)
    for p in by.values():
        reclassify_project(p, tools)
        if p.get('source_type') == 'official-seed':
            p['tracking_priority'] = 'track'

    save_jsonish('data/projects.yaml', list(by.values()))
    print(json.dumps({
        'normalized_new': len(recs),
        'total': len(by),
        'reclassified': len(by),
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
