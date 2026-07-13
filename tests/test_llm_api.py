"""Test the SenseNova API wrapper."""
import pytest
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class TestKeyRotation:
    def test_load_keys_from_auth_json(self):
        from llm_api import load_api_keys
        keys = load_api_keys()
        # Should load from ~/.hermes/auth.json credential pool
        assert isinstance(keys, list)
        # May be empty in test env, that's OK - just check structure
        for k in keys:
            assert isinstance(k, str)
            assert k.startswith('sk-')

    def test_key_rotation_round_robin(self):
        from llm_api import KeyRotator
        rotator = KeyRotator(['key1', 'key2', 'key3'])
        assert rotator.next() == 'key1'
        assert rotator.next() == 'key2'
        assert rotator.next() == 'key3'
        assert rotator.next() == 'key1'  # wraps around

    def test_key_rotation_skips_failed_keys(self):
        from llm_api import KeyRotator
        rotator = KeyRotator(['key1', 'key2', 'key3'])
        rotator.mark_failed('key2')
        assert rotator.next() == 'key1'
        assert rotator.next() == 'key3'  # skips key2
        assert rotator.next() == 'key1'

    def test_key_rotation_all_failed_resets(self):
        from llm_api import KeyRotator
        rotator = KeyRotator(['key1', 'key2'])
        rotator.mark_failed('key1')
        rotator.mark_failed('key2')
        # All failed -> reset and try again
        key = rotator.next()
        assert key in ['key1', 'key2']

    def test_empty_keys_raises(self):
        from llm_api import KeyRotator
        rotator = KeyRotator([])
        with pytest.raises(RuntimeError):
            rotator.next()


class TestParseJSONResponse:
    def test_parse_clean_json(self):
        from llm_api import parse_json_response
        text = '{"relevance_score": 0.85, "resource_type": ["mcp-server"]}'
        result = parse_json_response(text)
        assert result['relevance_score'] == 0.85
        assert result['resource_type'] == ['mcp-server']

    def test_parse_json_in_markdown_code_block(self):
        from llm_api import parse_json_response
        text = '```json\n{"relevance_score": 0.9}\n```'
        result = parse_json_response(text)
        assert result['relevance_score'] == 0.9

    def test_parse_json_with_surrounding_text(self):
        from llm_api import parse_json_response
        text = 'Here is my analysis:\n{"relevance_score": 0.7}\nDone.'
        result = parse_json_response(text)
        assert result['relevance_score'] == 0.7

    def test_parse_invalid_json_returns_none(self):
        from llm_api import parse_json_response
        assert parse_json_response('not json at all') is None
        assert parse_json_response('') is None
        assert parse_json_response(None) is None

    def test_parse_nested_json(self):
        from llm_api import parse_json_response
        text = '{"quality_detail": {"relevance": 9, "practicality": 8}}'
        result = parse_json_response(text)
        assert result['quality_detail']['relevance'] == 9

    def test_parse_json_with_code_block_no_language(self):
        from llm_api import parse_json_response
        text = '```\n{"relevance_score": 0.6}\n```'
        result = parse_json_response(text)
        assert result['relevance_score'] == 0.6


class TestCallWithRetry:
    def test_retry_on_auth_failure(self):
        """Test that call_with_retry rotates keys on auth failure."""
        from llm_api import call_with_retry, KeyRotator, RateLimitError
        rotator = KeyRotator(['bad-key1', 'bad-key2', 'bad-key3'])

        call_count = {'n': 0}
        def mock_call_llm(prompt, system_prompt, key, timeout=120):
            call_count['n'] += 1
            raise KeyError(f'Auth failed for {key}')

        with patch('llm_api.call_llm', side_effect=mock_call_llm):
            result = call_with_retry('test prompt', 'system', rotator, max_retries=3)
            assert result is None
            assert call_count['n'] == 3
