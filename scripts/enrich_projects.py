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
import subprocess
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
    try:
        r = run(cmd, timeout=60)
    except (subprocess.TimeoutExpired, OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        return None


def fetch_readme(full_name: str) -> str:
    """Fetch README base64 content via gh api.

    Never raises: network/timeouts/decode errors return empty string so
    bulk enrich can continue and mark the repo as checked.
    """
    cmd = f"gh api repos/{full_name}/readme --jq .content"
    try:
        r = run(cmd, timeout=60)
    except (subprocess.TimeoutExpired, OSError, subprocess.SubprocessError):
        return ""
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


def _missing_numeric(project: dict, key: str) -> bool:
    """True only when the key is absent (0 is a valid filled value)."""
    return key not in project or project.get(key) is None


def _missing_list(project: dict, key: str) -> bool:
    """True when key is absent or still the broken [None] sentinel.

    Empty list [] means we already queried GitHub and the repo has none —
    that is filled, not missing.
    """
    if key not in project:
        return True
    val = project.get(key)
    return val is None or val == [None]


def _missing_readme(project: dict) -> bool:
    """True when readme_preview was never successfully queried.

    Empty string is ambiguous historically (bulk --no-readme left many as '').
    Batch 3 treats empty as still needing a fetch attempt unless
    readme_checked is set, or the caller uses --readme-only with a
    separate marker.
    """
    if project.get("readme_checked") is True:
        return False
    return not project.get("readme_preview")


def needs_enrichment(project: dict, readme_only: bool = False) -> bool:
    repo = project.get("repo")
    if not repo or "/" not in str(repo):
        return False
    if readme_only:
        return _missing_readme(project)
    return (
        _missing_numeric(project, "forks")
        or not project.get("license")
        or _missing_list(project, "topics")
        or _missing_readme(project)
        or _missing_numeric(project, "stars")
        or _missing_list(project, "languages")
    )


def enrich_readme_only(project: dict) -> tuple[dict, bool, str]:
    """Fetch only readme_preview; always mark readme_checked for resume.

    Never raises. Timeouts / API failures mark the project checked with an
    empty preview so bulk runs can resume past bad repos.
    """
    repo = project.get("repo")
    if not repo or "/" not in str(repo):
        return project, False, "no-repo"
    if project.get("readme_checked") and project.get("readme_preview"):
        return project, False, "no-new-fields"
    if project.get("readme_checked") and not _missing_readme(project):
        return project, False, "no-new-fields"

    note = "ok"
    try:
        readme = fetch_readme(repo)
    except (subprocess.TimeoutExpired, OSError, subprocess.SubprocessError):
        readme = ""
        note = "timeout"
    except Exception:
        readme = ""
        note = "error"

    preview = clean_readme_preview(readme)
    project["readme_preview"] = preview  # may be "" for empty/missing README
    project["readme_checked"] = True
    if note in ("timeout", "error"):
        return project, True, note
    return project, True, "ok" if preview else "empty-readme"


def enrich_one(project: dict, readme_only: bool = False) -> tuple[dict, bool, str]:
    """Return (project, changed, status_note). Never raises to the pool."""
    try:
        return _enrich_one_impl(project, readme_only=readme_only)
    except (subprocess.TimeoutExpired, OSError, subprocess.SubprocessError):
        repo = project.get("repo") or "?"
        if readme_only or _missing_readme(project):
            project["readme_preview"] = project.get("readme_preview") or ""
            project["readme_checked"] = True
            return project, True, "timeout"
        return project, False, "timeout"
    except Exception:
        if readme_only or _missing_readme(project):
            project["readme_preview"] = project.get("readme_preview") or ""
            project["readme_checked"] = True
            return project, True, "error"
        return project, False, "error"


def _enrich_one_impl(project: dict, readme_only: bool = False) -> tuple[dict, bool, str]:
    repo = project.get("repo")
    if not repo or "/" not in str(repo):
        return project, False, "no-repo"

    if readme_only:
        return enrich_readme_only(project)

    data = gh_repo_view(repo)
    if not data:
        # Still try readme if missing — independent API
        if _missing_readme(project):
            return enrich_readme_only(project)
        return project, False, "gh-view-failed"

    changed = False

    if _missing_numeric(project, "forks") and data.get("forkCount") is not None:
        project["forks"] = data["forkCount"]
        changed = True

    if not project.get("license"):
        lic = extract_license(data)
        if lic:
            project["license"] = lic
            changed = True

    if _missing_numeric(project, "stars") and data.get("stargazerCount") is not None:
        project["stars"] = data["stargazerCount"]
        changed = True

    if _missing_list(project, "languages"):
        langs = extract_languages(data)
        # Always persist so resume skips repos with no language data
        project["languages"] = langs
        changed = True

    if _missing_list(project, "topics"):
        topics = extract_topics(data)
        # Always persist so empty topics don't get re-queried forever
        project["topics"] = topics
        changed = True

    if _missing_readme(project):
        readme = fetch_readme(repo)
        preview = clean_readme_preview(readme)
        project["readme_preview"] = preview  # persist empty as checked
        project["readme_checked"] = True
        changed = True

    return project, changed, "ok" if changed else "no-new-fields"


def main() -> None:
    ap = argparse.ArgumentParser(description="Enrich projects with GitHub data")
    ap.add_argument("--limit", type=int, default=None, help="Limit number of projects")
    ap.add_argument("--batch-size", type=int, default=3, help="Concurrent requests")
    ap.add_argument("--sleep", type=float, default=0.2, help="Sleep between batches (sec)")
    ap.add_argument(
        "--readme-only",
        action="store_true",
        help="Only fetch readme_preview (faster for bulk backfill)",
    )
    ap.add_argument(
        "--min-stars",
        type=int,
        default=None,
        help="Only enrich projects with stars >= this value",
    )
    args = ap.parse_args()

    projects = load_jsonish("data/projects.yaml")
    if not isinstance(projects, list):
        raise SystemExit("data/projects.yaml must be a list")

    # Keep object identity so in-place updates land in `projects`
    to_enrich = [p for p in projects if needs_enrichment(p, readme_only=args.readme_only)]
    if args.min_stars is not None:
        to_enrich = [p for p in to_enrich if (p.get("stars") or 0) >= args.min_stars]
    # Prefer high-star projects first for faster quality impact
    to_enrich.sort(key=lambda p: p.get("stars") or 0, reverse=True)
    if args.limit is not None:
        to_enrich = to_enrich[: args.limit]

    print(f"Total projects: {len(projects)}")
    print(f"Projects to enrich: {len(to_enrich)} (readme_only={args.readme_only})")

    enriched = 0
    failed = 0
    unchanged = 0
    empty_readme = 0
    total_batches = max(1, (len(to_enrich) + args.batch_size - 1) // args.batch_size)

    for i in range(0, len(to_enrich), args.batch_size):
        batch = to_enrich[i : i + args.batch_size]
        batch_no = i // args.batch_size + 1
        print(f"  Batch {batch_no}/{total_batches} ({len(batch)} projects)")

        with ThreadPoolExecutor(max_workers=args.batch_size) as executor:
            futures = {
                executor.submit(enrich_one, p, args.readme_only): p for p in batch
            }
            for future in as_completed(futures):
                orig = futures[future]
                try:
                    p, changed, note = future.result()
                except Exception as exc:
                    # Defense in depth: worker should not raise, but never kill bulk.
                    failed += 1
                    name = (orig.get("name") or orig.get("repo") or "?")[:40]
                    print(f"    FAIL {name} (worker-exception: {type(exc).__name__})")
                    if args.readme_only or _missing_readme(orig):
                        orig["readme_preview"] = orig.get("readme_preview") or ""
                        orig["readme_checked"] = True
                    continue

                name = (p.get("name") or p.get("repo") or "?")[:40]
                if changed:
                    enriched += 1
                    if note in ("empty-readme", "timeout", "error"):
                        empty_readme += 1
                        print(f"    EMPTY {name} ({note})" if note != "empty-readme" else f"    EMPTY {name}")
                    else:
                        print(f"    OK  {name}")
                elif note in ("gh-view-failed", "no-repo", "timeout", "error"):
                    failed += 1
                    print(f"    FAIL {name} ({note})")
                else:
                    unchanged += 1
                    print(f"    SKIP {name} ({note})")

        if batch_no % 5 == 0:
            save_jsonish("data/projects.yaml", projects)
            has_r = sum(1 for x in projects if x.get("readme_preview"))
            print(
                f"  Progress saved: enriched={enriched} failed={failed} "
                f"unchanged={unchanged} empty={empty_readme} readme_fill={has_r}/{len(projects)}"
            )

        if args.sleep and batch_no < total_batches:
            time.sleep(args.sleep)

    save_jsonish("data/projects.yaml", projects)
    has_r = sum(1 for x in projects if x.get("readme_preview"))
    print(
        f"\nDone: enriched={enriched}, failed={failed}, unchanged={unchanged}, "
        f"empty_readme={empty_readme}, requested={len(to_enrich)}, "
        f"readme_fill={has_r}/{len(projects)} ({100*has_r/max(1,len(projects)):.1f}%)"
    )


if __name__ == "__main__":
    main()
