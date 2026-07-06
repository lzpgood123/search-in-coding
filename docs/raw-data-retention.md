# Raw Data Retention and Archive Policy

`data/raw/` keeps collector evidence for traceability, but long-term raw JSON can grow quickly.

## Policy

- Keep recent raw folders in Git for easy audit.
- Archive older folders with `scripts/archive_raw.py`.
- Default mode is dry-run and safe.

## Commands

Dry run:

```bash
python3 scripts/archive_raw.py --keep-days 30
```

Apply archive:

```bash
python3 scripts/archive_raw.py --keep-days 30 --apply
```

Archives are written to:

```text
data/raw-archive/<source>/<YYYY-MM-DD>.tar.gz
```

## Notes

- Do not delete unarchived raw evidence.
- For very large archives, future work can move tarballs to GitHub Release assets.
