# Public Repository Publication Policy

This repository is public. Documentation and data must describe the project, not private work history, internal execution notes, account details, or server-specific operations.

## Do not publish

- Personal work experience, resume-style content, private identity, personal email, or account profile details.
- Account plans, subscription status, quota, billing, entitlement, or private support information.
- Secrets, tokens, API keys, credential hints, private URLs, local-only URLs, localhost URLs, or private IP addresses.
- Local machine paths such as `/root/...`, `/home/...`, `/Users/...`.
- Server implementation paths such as `/var/www/...`, `/etc/nginx/...`, or certificate paths.
- Hermes session process notes, Goal-mode transcripts, temporary execution plans, or internal cron prompts.
- Chat-style progress such as “I will”, “I have completed”, “the user asked”, or “this round executed”.

## Publish instead

- Stable project architecture.
- Public data contracts.
- Reproducible commands using repository-relative paths.
- Neutral automation descriptions.
- Public site and GitHub links.
- Source provenance and quality rules.
- Sanitized reports and generated site artifacts.

## Operational split

- GitHub Actions validate, build, test, and publish public artifacts.
- Production server deployment remains opt-in with `--deploy` and should be described neutrally, without local filesystem details.
- Internal Hermes cron configuration should live outside the public repository.

## Required pre-commit checks

```bash
python3 scripts/sanitize_public_data.py
python3 scripts/quality_gate.py
python3 -m pytest -q
git diff --check
```

Also scan for private terms before public commits.
