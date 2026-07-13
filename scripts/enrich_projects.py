#!/usr/bin/env python3
"""Enrich existing projects with missing GitHub data.

Fetches forks, license, stars, languages, topics, readme_preview
for all projects that have a repo field. Uses authenticated `gh` CLI.
Supports resume (skips already-filled fields) and periodic progress saves.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, load_jsonish, save_jsonish, run


REPO_FIELDS = (
    "nameWithOwner,forkCount,licenseInfo,stargazerCount,"
    "primaryLanguage,languages,repositoryTopics,description"
)


def gh_repo_view(full_name: str) -> dict | None:
    cmd = f"gh repo view {full_name} --json {REPO_FIELDS}"
    r = run(cmd, timeout=60)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        return None


def fetch_readme(full_name: str) -> str:
    cmd = f"gh api repos/{full_name}/readme --jq .content"
    r = run(cmd, timeout=60)
    if r.returncode != 0 or not (r.stdout or "").strip():
        return ""
    try:
        return base64.b64decode(r.stdout.strip()).decode("utf-8", errors="replace")
    except Exception:
        return ""


def extract_topics(data: dict) -> list[str]:
    topics_data = data.get("repositoryTopics") or []
    topics: list[str] = []
    if isinstance(topics_data, list):
        for t in topics_data:
            if isinstance(t, dict) and t.get("name"):
                topics.append(t["name"])
            elif isinstance(t, str) and t:
                topics.append(t)
    return topics


def extract_languages(data: dict) -> list[str]:
    langs: list[str] = []
    primary = data.get("primaryLanguage")
    if isinstance(primary, dict) and primary.get("name"):
        langs.append(primary["name"])

    all_langs = data.get("languages")
    # gh may return {nodes:[{name,size},...]} or a plain list
    if isinstance(all_langs, dict):
        nodes = all_langs.get("nodes") or all_langs.get("edges") or []
        if isinstance(nodes, list):
            for item in nodes:
                node = item.get("node", item) if isinstance(item, dict) else None
                if isinstance(node, dict) and node.get("name") and node["name"] not in langs:
                    langs.append(node["name"])
    elif isinstance(all_langs, list):
        for item in all_langs:
            if isinstance(item, dict) and item.get("name") and item["name"] not in langs:
                langs.append(item["name"])
            elif isinstance(item, str) and item and item not in langs:
                langs.append(item)
    return langs[:8]


def extract_license(data: dict) -> str | None:
    lic = data.get("licenseInfo")
    if not isinstance(lic, dict):
        return None
    for key in ("spdxId", "key", "name"):
        val = lic.get(key)
        if val and val not in ("NOASSERTION", "Other", "other"):
            # normalize key-like values
            if key == "key":
                return str(val).upper() if val == "unlicense" else str(val)
            return str(val)
    return None


def clean_readme_preview(readme: str, limit: int = 500) -> str:
    if not readme or len(readme) < 10:
        return ""
    clean = re.sub(r"<[^>]+>", "", readme)
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
    return clean[:limit]


def needs_enrichment(project: dict) -> bool:
    repo = project.get("repo")
    if not repo or "/" not in str(repo):
        return False
    langs = project.get("languages")
    bad_langs = (not langs) or langs == [None] or langs == []
    return (
        not project.get("forks")
        or not project.get("license")
        or not project.get("topics")
        or not project.get("readme_preview")
        or not project.get("stars")
        or bad_langs
    )


def enrich_one(project: dict) -> tuple[dict, bool, str]:
    """Return (project, changed, status_note)."""
    repo = project.get("repo")
    if not repo or "/" not in str(repo):
        return project, False, "no-repo"

    data = gh_repo_view(repo)
    if not data:
        return project, False, "gh-view-failed"

    changed = False

    if not project.get("forks") and data.get("forkCount") is not None:
        project["forks"] = data["forkCount"]
        changed = True

    if not project.get("license"):
        lic = extract_license(data)
        if lic:
            project["license"] = lic
            changed = True

    if not project.get("stars") and data.get("stargazerCount") is not None:
        project["stars"] = data["stargazerCount"]
        changed = True

    langs_existing = project.get("languages")
    if (not langs_existing) or langs_existing == [None] or langs_existing == []:
        langs = extract_languages(data)
        if langs:
            project["languages"] = langs
            changed = True

    if not project.get("topics"):
        topics = extract_topics(data)
        if topics:
            project["topics"] = topics
            changed = True

    if not project.get("readme_preview"):
        readme = fetch_readme(repo)
        preview = clean_readme_preview(readme)
        if preview:
            project["readme_preview"] = preview
            changed = True

    return project, changed, "ok" if changed else "no-new-fields"


def main() -> None:
    ap = argparse.ArgumentParser(description="Enrich projects with GitHub data")
    ap.add_argument("--limit", type=int, default=None, help="Limit number of projects")
    ap.add_argument("--batch-size", type=int, default=3, help="Concurrent requests")
    ap.add_argument("--sleep", type=float, default=0.2, help="Sleep between batches (sec)")
    args = ap.parse_args()

    projects = load_jsonish("data/projects.yaml")
    if not isinstance(projects, list):
        raise SystemExit("data/projects.yaml must be a list")

    # Keep object identity so in-place updates land in `projects`
    to_enrich = [p for p in projects if needs_enrichment(p)]
    if args.limit is not None:
        to_enrich = to_enrich[: args.limit]

    print(f"Total projects: {len(projects)}")
    print(f"Projects to enrich: {len(to_enrich)}")

    enriched = 0
    failed = 0
    unchanged = 0
    total_batches = max(1, (len(to_enrich) + args.batch_size - 1) // args.batch_size)

    for i in range(0, len(to_enrich), args.batch_size):
        batch = to_enrich[i : i + args.batch_size]
        batch_no = i // args.batch_size + 1
        print(f"  Batch {batch_no}/{total_batches} ({len(batch)} projects)")

        with ThreadPoolExecutor(max_workers=args.batch_size) as executor:
            futures = {executor.submit(enrich_one, p): p for p in batch}
            for future in as_completed(futures):
                p, changed, note = future.result()
                name = (p.get("name") or p.get("repo") or "?")[:40]
                if changed:
                    enriched += 1
                    print(f"    OK  {name}")
                elif note in ("gh-view-failed", "no-repo"):
                    failed += 1
                    print(f"    FAIL {name} ({note})")
                else:
                    unchanged += 1
                    print(f"    SKIP {name} ({note})")

        if batch_no % 5 == 0:
            save_jsonish("data/projects.yaml", projects)
            print(f"  Progress saved: enriched={enriched} failed={failed} unchanged={unchanged}")

        if args.sleep and batch_no < total_batches:
            time.sleep(args.sleep)

    save_jsonish("data/projects.yaml", projects)
    print(
        f"\nDone: enriched={enriched}, failed={failed}, unchanged={unchanged}, "
        f"requested={len(to_enrich)}"
    )


if __name__ == "__main__":
    main()
