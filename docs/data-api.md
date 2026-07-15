# Agent EcoRadar Data API

The static site publishes machine-readable JSON files under `/data/`.

Base URL:

```text
https://ecoradar.lzpgood.online/data/
```

## Endpoints

```text
/data/projects.json
/data/curated-projects.json
/data/rejected-projects.json
/data/tools.json
/data/concepts.json
/data/metrics.json
/data/i18n.json
```

## Example

```bash
curl https://ecoradar.lzpgood.online/data/curated-projects.json
```

## Record contract

Important fields:

- `id`
- `name`
- `url`
- `source_type`
- `record_kind`
- `source_quality`
- `ranking_scope`
- `review_state`: `auto-indexed`, `auto-curated`, `auto-rejected`
- `i18n.zh/en`
- `score`
- `score_reason`
- `total_score`

The public API contains no private account quota, subscription, token, or credential information.
