"""Test the summary translation script."""
import pytest
import sys
import json
import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class TestCacheKey:
    def test_cache_key_is_md5_prefix(self):
        from translate_summaries import cache_key
        url = 'https://github.com/foo/bar'
        expected = hashlib.md5(url.encode('utf-8')).hexdigest()[:16]
        assert cache_key(url) == expected

    def test_cache_key_deterministic(self):
        from translate_summaries import cache_key
        assert cache_key('https://github.com/a/b') == cache_key('https://github.com/a/b')


class TestCacheIO:
    def test_get_cached_returns_none_if_not_exists(self, tmp_path):
        from translate_summaries import get_cached
        with patch('translate_summaries.CACHE_DIR', tmp_path):
            assert get_cached('https://github.com/nonexistent/repo') is None

    def test_save_and_get_cached(self, tmp_path):
        from translate_summaries import save_cached, get_cached
        with patch('translate_summaries.CACHE_DIR', tmp_path):
            url = 'https://github.com/foo/bar'
            data = {'zh': '这是中文摘要', 'en': 'This is English summary'}
            save_cached(url, data)
            result = get_cached(url)
            assert result is not None
            assert result['zh'] == '这是中文摘要'
            assert result['en'] == 'This is English summary'


class TestNeedsTranslation:
    def test_english_summary_needs_translation(self):
        from translate_summaries import needs_translation
        project = {
            'summary': 'A CLI tool for AI coding',
            'i18n': {'zh': {'summary': 'A CLI tool for AI coding'}, 'en': {'summary': 'A CLI tool for AI coding'}}
        }
        assert needs_translation(project) is True

    def test_already_translated_skips(self):
        from translate_summaries import needs_translation
        project = {
            'summary': 'A CLI tool for AI coding',
            'i18n': {'zh': {'summary': '一个 AI 编程的命令行工具'}, 'en': {'summary': 'A CLI tool for AI coding'}}
        }
        assert needs_translation(project) is False

    def test_empty_summary_skips(self):
        from translate_summaries import needs_translation
        project = {'summary': '', 'i18n': {}}
        assert needs_translation(project) is False

    def test_already_has_chinese_skips(self):
        from translate_summaries import needs_translation
        project = {
            'summary': '这是一个中文描述',
            'i18n': {'zh': {'summary': '这是一个中文描述'}, 'en': {'summary': '这是一个中文描述'}}
        }
        assert needs_translation(project) is False


class TestLoadApiKeys:
    def test_load_keys_from_auth_json(self):
        from translate_summaries import load_api_keys
        keys = load_api_keys()
        assert isinstance(keys, list)
        for k in keys:
            assert isinstance(k, str)
            assert k.startswith('sk-')

    def test_no_auth_file_returns_empty(self, tmp_path):
        from translate_summaries import load_api_keys
        with patch.object(Path, 'home', return_value=tmp_path):
            keys = load_api_keys()
            assert keys == []


class TestKeyRotator:
    def test_round_robin(self):
        from translate_summaries import KeyRotator
        rotator = KeyRotator(['key1', 'key2', 'key3'])
        assert rotator.next() == 'key1'
        assert rotator.next() == 'key2'
        assert rotator.next() == 'key3'
        assert rotator.next() == 'key1'

    def test_skips_failed_keys(self):
        from translate_summaries import KeyRotator
        rotator = KeyRotator(['key1', 'key2', 'key3'])
        rotator.mark_failed('key2')
        assert rotator.next() == 'key1'
        assert rotator.next() == 'key3'

    def test_all_failed_resets(self):
        from translate_summaries import KeyRotator
        rotator = KeyRotator(['key1', 'key2'])
        rotator.mark_failed('key1')
        rotator.mark_failed('key2')
        # Should reset and return a key
        k = rotator.next()
        assert k in ('key1', 'key2')


class TestBuildPrompt:
    def test_prompt_contains_summary(self):
        from translate_summaries import build_translation_prompt
        prompt = build_translation_prompt('A great CLI tool for coding')
        assert 'A great CLI tool for coding' in prompt
        assert '中文' in prompt or 'Chinese' in prompt.lower() or 'translate' in prompt.lower()


class TestParseTranslation:
    def test_parse_direct_json(self):
        from translate_summaries import parse_translation
        assert parse_translation('{"translated": "中文摘要"}') == '中文摘要'

    def test_parse_markdown_code_block(self):
        from translate_summaries import parse_translation
        text = '```json\n{"translated": "中文摘要"}\n```'
        assert parse_translation(text) == '中文摘要'

    def test_parse_raw_chinese_fallback(self):
        from translate_summaries import parse_translation
        assert parse_translation('这是直接返回的中文') == '这是直接返回的中文'

    def test_parse_empty_returns_none(self):
        from translate_summaries import parse_translation
        assert parse_translation('') is None
        assert parse_translation(None) is None
