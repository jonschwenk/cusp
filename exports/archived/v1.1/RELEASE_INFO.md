# CUSP Release v1.1

## Summary

- Dataset version: `v1.1`
- Code version: `0.1`
- Git commit: `4c02da7b2755d76ea427d124f146ecd2cc69d8ed`
- Generated at (UTC): `2026-08-06T20:05:34.551586+00:00`
- Canonical rows: `79389`
- Included sources: `57`
- Date range: `1952-06-01` to `2024-10-11`
- Feature export: not included

## Exported Artifacts

| File | Rows | Size (bytes) | SHA-256 | Note |
|---|---:|---:|---|---|
| `cusp_v1.1.csv` | 79389 | 9139558 | `75e2acba72087156b14b6d980c97a3cb440a52484a10f274da52736456e7b039` | Canonical CUSP dataset. |
| `cusp_sources_v1.1.bib` | 57 | 22005 | `d540aca9968cc72f85b201a72ce92cdde8a10f64d12d27c16738db8bab3b767c` | BibTeX entries for all sources present in the canonical release. |

## Changes In This Release

- Added the canonical `quality_flags` field and its maintained flag vocabulary.
- Standardized dense GPR surveys to one mean observation per occupied 5 m cell,
  reducing artificial point-density dominance while preserving distinct survey
  dates and thaw years.
- Preferred original observation sources over later syntheses and removed known
  overlaps, including Jafarov/Moore, CALM-derived records, NCSS/Pastick,
  Chapin/Ruess, Smith/Burgess, Walker/Peirce, and Natali/FireALT cases.
- Added direct sources including CALM, NCSS Lab Data Mart, PERMOS, ViPER,
  Veremeeva et al., Fisher, Pawley, Barrow CALM U1, and Utqiagvik field data;
  corrected the Bonnaventure source key and attribution.
- Corrected source-specific coordinates, dates, observation limits, and
  presence/absence semantics; retained visually interpreted Koyukuk records
  with explicit quality flags.
- Generated citation metadata from the authoritative BibTeX file and completed
  source-level processing metadata for all 57 included sources.
- Defined the official release as a data-only bundle. Environmental feature
  sampling remains available as an optional derived workflow and is not
  included in v1.1.

## Citation Notes

- The canonical dataset file is `cusp_v1.1.csv`.
- The master bibliography file is `cusp_sources_v1.1.bib`.
- To extract only the entries you need from a filtered CUSP table, run:

```bash
python -m cusp.citations --input path/to/your_cusp_table.csv --output references.bib
```
