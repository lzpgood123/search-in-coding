#!/usr/bin/env python3
"""SenseNova API wrapper with key rotation and retry.

Calls OpenAI-compatible chat/completions endpoint at https://token.sensenova.cn/v1
Uses 13 API keys from ~/.hermes/auth.json with round-robin rotation.
"""
import json
import os
import re
import time
import urllib.request
import urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = 'https://token.sensenova.cn/v1/chat/completions'
MODEL = 'deepseek-v4-flash'


class RateLimitError(Exception):
    """Raised when API returns 429 rate limit."""
    pass


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
            # All keys failed, reset and try again
            self.failed.clear()
            available = self.keys
        if not available:
            raise RuntimeError('No API keys available')
        # Find next available key
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


def parse_json_response(text):
    """Extract JSON from LLM response text. Handles code blocks and surrounding text."""
    if not text:
        return None
    text = text.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    md_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if md_match:
        try:
            return json.loads(md_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding JSON object in text (handles nested braces)
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # Last resort: try finding any JSON-like structure with deeper nesting
    # Find the first { and last } and try to parse
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    return None


def call_llm(prompt, system_prompt=None, key=None, timeout=120):
    """Call SenseNova API with a single prompt. Returns response text or None."""
    if key is None:
        raise ValueError('API key required')

    messages = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    messages.append({'role': 'user', 'content': prompt})

    payload = {
        'model': MODEL,
        'messages': messages,
        'temperature': 0.3,  # low temperature for consistent analysis
        'max_tokens': 2000,
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        BASE_URL,
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
        print(f'  API error {e.code}: {error_body}')
        if e.code in (401, 403):
            raise KeyError(f'Auth failed: {e.code}')
        if e.code == 429:
            raise RateLimitError('Rate limited')
        return None
    except (urllib.error.URLError, TimeoutError) as e:
        print(f'  Network error: {e}')
        return None


def call_with_retry(prompt, system_prompt, rotator, max_retries=3):
    """Call LLM with key rotation and retry on failure."""
    last_error = None
    for attempt in range(max_retries):
        key = None
        try:
            key = rotator.next()
            result = call_llm(prompt, system_prompt, key=key)
            if result:
                return result
        except KeyError:
            # Auth failed, mark key as failed
            if key is not None:
                rotator.mark_failed(key)
            print(f'  Key failed, rotating... (attempt {attempt+1}/{max_retries})')
        except RateLimitError:
            time.sleep(5 * (attempt + 1))  # exponential backoff
            print(f'  Rate limited, waiting... (attempt {attempt+1}/{max_retries})')
        except Exception as e:
            last_error = e
            print(f'  Error: {e} (attempt {attempt+1}/{max_retries})')
    print(f'  All retries exhausted: {last_error}')
    return None


def batch_analyze(items, prompt_fn, system_prompt, max_workers=3):
    """Analyze a batch of items concurrently.

    Args:
        items: list of items to analyze
        prompt_fn: function(item) -> prompt string
        system_prompt: system prompt string
        max_workers: concurrent workers (default 3)

    Returns:
        dict mapping item index to parsed JSON result (or None if failed)
    """
    keys = load_api_keys()
    if not keys:
        print('ERROR: No API keys found')
        return {}

    rotator = KeyRotator(keys)
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for i, item in enumerate(items):
            prompt = prompt_fn(item)
            future = executor.submit(call_with_retry, prompt, system_prompt, rotator)
            futures[future] = i

        for future in as_completed(futures):
            idx = futures[future]
            try:
                text = future.result()
                if text:
                    results[idx] = parse_json_response(text)
                else:
                    results[idx] = None
            except Exception as e:
                print(f'  Item {idx} failed: {e}')
                results[idx] = None

    return results
