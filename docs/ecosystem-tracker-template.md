# Ecosystem Tracker Template Notes

Search in Coding can be reused as a template for other ecosystem trackers.

## Replaceable inputs

- `data/seed-tools.yaml`: target tools.
- `data/queries.yaml`: discovery queries.
- `data/concepts.yaml`: taxonomy concepts.
- `config/scoring.yaml`: scoring and curation policy.

## Pipeline

```text
collect -> normalize -> enrich_i18n -> score -> finalize -> translation enrichment -> reports -> snapshot diff -> site build -> quality gate -> optional deploy
```

## Reuse checklist

1. Define target tools and aliases.
2. Define source queries.
3. Define category taxonomy and scoring weights.
4. Run `python3 scripts/update_tracker.py --skip-collect` for dry rebuild.
5. Deploy only with `--deploy`.

Potential future trackers:

- MCP ecosystem.
- AI IDE ecosystem.
- Agent framework ecosystem.
- China AI tool ecosystem.
