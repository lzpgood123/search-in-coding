#!/usr/bin/env python3
"""Benchmark reference manager.

Maintains reference projects for each score range.
Used to calibrate LLM quality scoring.
"""
import json
from pathlib import Path

BENCHMARK_RANGES = [
    {'label': '标杆', 'min': 81, 'max': 100, 'description': '生态标杆项目'},
    {'label': '优秀', 'min': 61, 'max': 80, 'description': '高质量生态项目'},
    {'label': '可用', 'min': 41, 'max': 60, 'description': '可用项目'},
    {'label': '萌芽', 'min': 21, 'max': 40, 'description': '早期项目'},
    {'label': '噪声', 'min': 0, 'max': 20, 'description': '低质量或无关项目'},
]


def score_to_range(score):
    """Map a score to its benchmark range label."""
    for r in BENCHMARK_RANGES:
        if r['min'] <= score <= r['max']:
            return r['label']
    return '噪声'


class BenchmarkManager:
    """Manage benchmark reference projects in data/benchmarks.yaml."""

    def __init__(self, path=None):
        if path is None:
            from common import ROOT
            path = ROOT / 'data' / 'benchmarks.yaml'
        self.path = Path(path)

    def load(self):
        """Load existing benchmarks."""
        if not self.path.exists():
            return {}
        try:
            import yaml
            data = yaml.safe_load(self.path.read_text(encoding='utf-8'))
            return data or {}
        except Exception:
            return {}

    def save(self, benchmarks):
        """Save benchmarks to file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        import yaml
        self.path.write_text(
            yaml.dump(benchmarks, allow_unicode=True, default_flow_style=False, sort_keys=False),
            encoding='utf-8'
        )

    def get_benchmark_for_score(self, score):
        """Get the benchmark reference for a given score."""
        label = score_to_range(score)
        benchmarks = self.load()
        return benchmarks.get(label)

    def group_by_range(self, projects):
        """Group projects by their benchmark range."""
        groups = {r['label']: [] for r in BENCHMARK_RANGES}
        for p in projects:
            label = score_to_range(p.get('total_score', 0))
            groups[label].append(p)
        return groups

    def update_from_llm(self, llm_result, projects):
        """Update benchmarks from LLM selection result.

        Args:
            llm_result: dict from LLM with 'benchmarks' key
            projects: list of all projects (to resolve IDs)
        """
        benchmarks = self.load()
        project_map = {p['id']: p for p in projects}
        llm_benchmarks = llm_result.get('benchmarks', {})

        for label, info in llm_benchmarks.items():
            pid = info.get('project_id')
            if pid and pid in project_map:
                p = project_map[pid]
                benchmarks[label] = {
                    'project_id': pid,
                    'project_name': p.get('name', ''),
                    'score': p.get('total_score', 0),
                    'reason': info.get('reason', ''),
                }
            else:
                # Keep existing if LLM selected an invalid project
                print(f'  Warning: LLM selected unknown project {pid} for {label}')

        self.save(benchmarks)
        return benchmarks
