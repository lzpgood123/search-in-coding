#!/usr/bin/env python3
"""Batch-translate project summaries to Chinese using SenseNova API.

Reads projects.yaml, translates each project's English summary to Chinese
via DeepSeek-V4-Flash, caches results by URL hash, and writes translations
back into i18n.zh.summary.

Usage:
    python3 scripts/translate_summaries.py              # translate all
    python3 scripts/translate_summaries.py --limit 5    # translate only 5
    python3 scripts/translate_summaries.py --dry-run    # show what would be done
"""
import argparse
import hashlib
import json
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ensure scripts/ is on sys.path for common import
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT, load_jsonish, save_jsonish

# === Constants ===

API_URL = 'https://token.sensenova.cn/v1/chat/completions'
MODEL = 'deepseek-v4-flash'
CACHE_DIR = ROOT / 'data' / 'translations-cache'
MAX_WORKERS = 3  # concurrent translation requests

TRANSLATION_SYSTEM = (
    "You are a professional translator specializing in software and AI technology. "
    "Translate the given English text into natural, fluent Chinese (Simplified). "
    "Keep technical terms, project names, and proper nouns in English. "
    "Respond with JSON only: {\"translated\": \"translated text\"}"
)


# === API Key Management ===

def load_api_keys():
    """Load API keys from ~/.hermes/auth.json credential pool."""
    auth_path = Path.home() / '.hermes' / 'auth.json'
    if not auth_path.exists():
        return []
    try:
        data = json.loads(auth_path.read_text(encoding='utf-8'))
        pool = data.get('credential_pool', {}).get('custom:sensenova', [])
        keys = []
        for entry in pool:
            if isinstance(entry, dict):
                key = entry.get('access_token', '')
                if key and key.startswith('sk-'):
                    keys.append(key)
            elif isinstance(entry, str) and entry.startswith('sk-'):
                keys.append(entry)
        return keys
    except (json.JSONDecodeError, KeyError):
        return []


class KeyRotator:
    """Round-robin key rotation with failure tracking."""

    def __init__(self, keys):
        self.keys = list(keys)
        self.index = 0
        self.failed = set()

    def next(self):
        available = [k for k in self.keys if k not in self.failed]
        if not available:
            self.failed.clear()
            available = self.keys
        if not available:
            raise RuntimeError('No API keys available')
        for _ in range(len(self.keys)):
            k = self.keys[self.index % len(self.keys)]
            self.index += 1
            if k not in self.failed:
                return k
        return available[0]

    def mark_failed(self, key):
        self.failed.add(key)

    def reset(self):
        self.failed.clear()


# === Cache ===

def cache_key(url):
    """Generate cache key from URL (md5 hex, first 16 chars)."""
    return hashlib.md5(url.encode('utf-8')).hexdigest()[:16]


def get_cached(url):
    """Get cached translation by URL."""
    key = cache_key(url)
    path = CACHE_DIR / f'{key}.json'
    if path.exists():
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            return None
    return None


def save_cached(url, translation):
    """Save translation to cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = cache_key(url)
    path = CACHE_DIR / f'{key}.json'
    path.write_text(
        json.dumps(translation, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )


# === Translation Logic ===

def needs_translation(project):
    """Check if a project's summary needs translation.

    Returns True if:
    - summary is non-empty
    - summary contains English text (not already Chinese)
    - i18n.zh.summary is missing or identical to English summary
    """
    summary = project.get('summary', '')
    if not summary or len(summary) < 5:
        return False

    # Already has Chinese? Skip.
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', summary))
    if has_chinese:
        return False

    zh_summary = ''
    i18n = project.get('i18n', {})
    if isinstance(i18n, dict):
        zh = i18n.get('zh', {})
        if isinstance(zh, dict):
            zh_summary = zh.get('summary', '')

    # If zh.summary already differs from English, it's translated.
    if zh_summary and zh_summary != summary:
        return False

    return True


def build_translation_prompt(summary):
    """Build the LLM prompt for translating a summary."""
    return f"""Translate the following English text to Chinese (Simplified):

{summary[:500]}

Respond with JSON: {{"translated": "translated text here"}}"""


def call_llm(prompt, system_prompt, key, timeout=60):
    """Call SenseNova API. Returns response text or None."""
    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': prompt},
    ]
    payload = {
        'model': MODEL,
        'messages': messages,
        'temperature': 0.3,
        'max_tokens': 1000,
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {key}',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result.get('choices', [{}])[0].get('message', {}).get('content', '')
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')[:500] if e.fp else ''
        if e.code in (401, 403):
            raise KeyError(f'Auth failed: {e.code}')
        if e.code == 429:
            raise RateLimitError('Rate limited')
        print(f'  API error {e.code}: {error_body}')
        return None
    except (urllib.error.URLError, TimeoutError) as e:
        print(f'  Network error: {e}')
        return None


class RateLimitError(Exception):
    pass


def translate_with_retry(prompt, system_prompt, rotator, max_retries=3):
    """Translate with key rotation and retry."""
    for attempt in range(max_retries):
        key = None
        try:
            key = rotator.next()
            result = call_llm(prompt, system_prompt, key)
            if result:
                return result
        except KeyError:
            if key is not None:
                rotator.mark_failed(key)
            print(f'  Key failed, rotating... (attempt {attempt+1}/{max_retries})')
        except RateLimitError:
            time.sleep(5 * (attempt + 1))
            print(f'  Rate limited, waiting... (attempt {attempt+1}/{max_retries})')
        except Exception as e:
            print(f'  Error: {e} (attempt {attempt+1}/{max_retries})')
    print(f'  All retries exhausted')
    return None


def parse_translation(text):
    """Extract translated text from LLM response."""
    if not text:
        return None
    text = text.strip()
    # Try direct JSON parse
    try:
        data = json.loads(text)
        return data.get('translated')
    except json.JSONDecodeError:
        pass
    # Try extracting from markdown code block
    md_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if md_match:
        try:
            data = json.loads(md_match.group(1).strip())
            return data.get('translated')
        except json.JSONDecodeError:
            pass
    # Try finding JSON object
    json_match = re.search(r'\{[^}]+\}', text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            return data.get('translated')
        except json.JSONDecodeError:
            pass
    # Fallback: use raw text if it looks like Chinese
    if re.search(r'[\u4e00-\u9fff]', text):
        return text.strip()
    return None


def translate_one(project, rotator):
    """Translate a single project's summary.

    Returns (project_id, translated_zh_summary) or (project_id, None).
    """
    url = project.get('url', '')
    summary = project.get('summary', '')

    # Check cache first
    cached = get_cached(url)
    if cached and cached.get('zh'):
        return project.get('id'), cached['zh']

    # Call LLM
    prompt = build_translation_prompt(summary)
    raw = translate_with_retry(prompt, TRANSLATION_SYSTEM, rotator)
    if not raw:
        return project.get('id'), None

    zh = parse_translation(raw)
    if not zh:
        return project.get('id'), None

    # Cache result
    save_cached(url, {'zh': zh, 'en': summary})
    return project.get('id'), zh


def run_translation(projects, limit=None, dry_run=False):
    """Run batch translation on projects.

    Args:
        projects: list of project dicts
        limit: max number of projects to translate (None = all)
        dry_run: if True, only report what would be done

    Returns:
        (total, translated_count, skipped_count, failed_count)
    """
    # Filter projects needing translation
    to_translate = [p for p in projects if needs_translation(p)]
    if limit:
        to_translate = to_translate[:limit]

    total = len(to_translate)
    print(f'Projects needing translation: {total}')
    print(f'Total projects in file: {len(projects)}')

    if dry_run:
        for p in to_translate[:10]:
            print(f'  - {p.get("id")}: {p.get("summary", "")[:60]}...')
        if total > 10:
            print(f'  ... and {total - 10} more')
        return total, 0, 0, 0

    keys = load_api_keys()
    if not keys:
        print('ERROR: No API keys found in ~/.hermes/auth.json')
        return total, 0, 0, total

    print(f'Loaded {len(keys)} API keys')
    rotator = KeyRotator(keys)

    translated_count = 0
    skipped_count = 0
    failed_count = 0

    # Build translation tasks
    tasks = {p.get('id'): p for p in to_translate}
    results = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for pid, project in tasks.items():
            future = executor.submit(translate_one, project, rotator)
            futures[future] = pid

        for future in as_completed(futures):
            pid = futures[future]
            try:
                proj_id, zh = future.result()
                if zh:
                    results[pid] = zh
                    translated_count += 1
                else:
                    failed_count += 1
                    print(f'  FAILED: {pid}')
            except Exception as e:
                failed_count += 1
                print(f'  EXCEPTION: {pid}: {e}')

            # Progress
            done = translated_count + failed_count + skipped_count
            if done % 10 == 0 or done == total:
                print(f'  Progress: {done}/{total} (translated={translated_count}, failed={failed_count})')

    # Write translations back to projects
    for p in projects:
        pid = p.get('id')
        if pid in results:
            i18n = p.setdefault('i18n', {})
            zh = i18n.setdefault('zh', {})
            zh['summary'] = results[pid]
            # Also ensure en.summary is set
            en = i18n.setdefault('en', {})
            if not en.get('summary'):
                en['summary'] = p.get('summary', '')

    print(f'\nTranslation complete: {translated_count} translated, {failed_count} failed')
    return total, translated_count, skipped_count, failed_count


# === Main ===

def main():
    parser = argparse.ArgumentParser(description='Batch translate project summaries to Chinese')
    parser.add_argument('--limit', type=int, default=None, help='Max projects to translate')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be translated')
    parser.add_argument('--file', default='data/projects.yaml', help='Data file to read/write')
    args = parser.parse_args()

    print(f'=== Summary Translation ===')
    projects = load_jsonish(args.file)
    print(f'Loaded {len(projects)} projects from {args.file}')

    total, translated, skipped, failed = run_translation(
        projects, limit=args.limit, dry_run=args.dry_run
    )

    if not args.dry_run and translated > 0:
        save_jsonish(args.file, projects)
        print(f'Saved {len(projects)} projects to {args.file}')
        print(f'Cache files in: {CACHE_DIR}')

    # Exit code: 0 if all succeeded, 1 if any failed
    sys.exit(1 if failed > 0 else 0)


if __name__ == '__main__':
    main()
