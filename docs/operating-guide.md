# Operating Guide

## Daily discovery

This repository is the long-running source of truth for the AI Coding Agent ecosystem tracker. Results should be committed back to `main` after quality gates pass.

Preferred one-command update:

```bash
python3 scripts/update_tracker.py --github-limit 20 --exa-limit 3
```

The update script:

1. Collects GitHub results with `gh`.
2. Collects Exa semantic search results with `mcporter` when available.
3. Normalizes, scores, finalizes, regenerates reports, builds the site, and runs quality gates.
4. Leaves all changes in the working tree for review/commit.

Manual fallback:

```bash
python3 scripts/collect_github.py --limit 20
python3 scripts/collect_exa.py --limit 3 || python3 scripts/collect_web.py --limit 5
python3 scripts/normalize.py --source all
python3 scripts/score.py
python3 scripts/finalize_data.py
python3 scripts/generate_reports.py
python3 scripts/build_site.py
python3 scripts/quality_gate.py
```

## Weekly report

```bash
python3 scripts/finalize_data.py
python3 scripts/generate_reports.py
python3 scripts/build_site.py
python3 scripts/quality_gate.py
```

## Monthly audit

Review `data/curated-projects.yaml`, `data/rejected-projects.yaml`, and `docs/reports/source-quality-audit.md`.

## Production scheduler setup

A production scheduler should run from this repository, pull latest `main`, execute `scripts/update_tracker.py`, commit meaningful changes, and push back to GitHub. GitHub Actions also runs daily as a second automation layer.


Production deployment uses `SEARCH_IN_CODING_WEBROOT` or `scripts/deploy_site.py --dest <webroot>`; concrete server paths should stay outside public docs.
