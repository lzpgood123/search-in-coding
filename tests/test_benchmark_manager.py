"""Test benchmark reference management."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class TestBenchmarkRanges:
    def test_score_to_range(self):
        from benchmark_manager import score_to_range
        assert score_to_range(95) == '标杆'
        assert score_to_range(81) == '标杆'
        assert score_to_range(80) == '优秀'
        assert score_to_range(61) == '优秀'
        assert score_to_range(60) == '可用'
        assert score_to_range(41) == '可用'
        assert score_to_range(40) == '萌芽'
        assert score_to_range(21) == '萌芽'
        assert score_to_range(20) == '噪声'
        assert score_to_range(0) == '噪声'

    def test_range_labels(self):
        from benchmark_manager import BENCHMARK_RANGES
        labels = [r['label'] for r in BENCHMARK_RANGES]
        assert labels == ['标杆', '优秀', '可用', '萌芽', '噪声']


class TestBenchmarkManager:
    def test_load_empty_benchmarks(self, tmp_path):
        from benchmark_manager import BenchmarkManager
        bm = BenchmarkManager(tmp_path / 'benchmarks.yaml')
        benchmarks = bm.load()
        assert benchmarks == {} or benchmarks is not None

    def test_save_and_load_benchmarks(self, tmp_path):
        from benchmark_manager import BenchmarkManager
        bm = BenchmarkManager(tmp_path / 'benchmarks.yaml')
        bm.save({
            '标杆': {'project_id': 'test-1', 'project_name': 'Test', 'reason': 'top project'},
        })
        loaded = bm.load()
        assert '标杆' in loaded
        assert loaded['标杆']['project_id'] == 'test-1'

    def test_get_benchmark_for_score(self, tmp_path):
        from benchmark_manager import BenchmarkManager
        bm = BenchmarkManager(tmp_path / 'benchmarks.yaml')
        bm.save({
            '标杆': {'project_id': 'ref-1'},
            '优秀': {'project_id': 'ref-2'},
            '可用': {'project_id': 'ref-3'},
            '萌芽': {'project_id': 'ref-4'},
            '噪声': {'project_id': 'ref-5'},
        })
        assert bm.get_benchmark_for_score(90)['project_id'] == 'ref-1'
        assert bm.get_benchmark_for_score(70)['project_id'] == 'ref-2'
        assert bm.get_benchmark_for_score(50)['project_id'] == 'ref-3'
        assert bm.get_benchmark_for_score(30)['project_id'] == 'ref-4'
        assert bm.get_benchmark_for_score(10)['project_id'] == 'ref-5'

    def test_group_projects_by_range(self, tmp_path):
        from benchmark_manager import BenchmarkManager
        bm = BenchmarkManager(tmp_path / 'benchmarks.yaml')
        projects = [
            {'id': '1', 'total_score': 90},
            {'id': '2', 'total_score': 70},
            {'id': '3', 'total_score': 50},
            {'id': '4', 'total_score': 30},
            {'id': '5', 'total_score': 10},
        ]
        grouped = bm.group_by_range(projects)
        assert len(grouped['标杆']) == 1
        assert len(grouped['优秀']) == 1
        assert len(grouped['可用']) == 1
        assert len(grouped['萌芽']) == 1
        assert len(grouped['噪声']) == 1

    def test_update_from_llm(self, tmp_path):
        from benchmark_manager import BenchmarkManager
        bm = BenchmarkManager(tmp_path / 'benchmarks.yaml')
        projects = [
            {'id': 'p1', 'name': 'Project 1', 'total_score': 90},
            {'id': 'p2', 'name': 'Project 2', 'total_score': 50},
        ]
        llm_result = {
            'benchmarks': {
                '标杆': {'project_id': 'p1', 'reason': 'Top project'},
                '可用': {'project_id': 'p2', 'reason': 'Decent project'},
            }
        }
        bm.update_from_llm(llm_result, projects)
        loaded = bm.load()
        assert loaded['标杆']['project_id'] == 'p1'
        assert loaded['标杆']['project_name'] == 'Project 1'
        assert loaded['标杆']['score'] == 90
        assert loaded['可用']['project_id'] == 'p2'
