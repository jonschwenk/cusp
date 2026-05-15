# CUSP Release v1.0

## Summary

- Dataset version: `v1.0`
- Code version: `0.1`
- Git commit: `c61d80d46b13e38ce67094b1fd01e278812df605`
- Generated at (UTC): `2026-05-06T17:24:00.092081+00:00`
- Canonical rows: `239473`
- Included sources: `50`
- Date range: `1962-08-15` to `2024-10-03`
- Feature export: included as `cusp_features_v1.0.csv`

## Exported Artifacts

| File | Rows | Size (bytes) | SHA-256 | Note |
|---|---:|---:|---|---|
| `cusp_v1.0.csv` | 239473 | 27034230 | `637f0c51636370ad49093c430a010f7e3106a49468e2b49cd6752c01ee1d1268` | Canonical CUSP dataset. |
| `cusp_features_v1.0.csv` | 239473 | 69199349 | `d6b81568a7292e3a355f02ddceeed440a862d5bb32002043458f0cabeed486f5` | Observation-level GEE feature table keyed to cusp_obs_id. |
| `cusp_sources_v1.0.bib` | 50 | 17641 | `09ea1e8afe56b726bb213bd374628347e141a369c43ce065d54b6ce42367d6d8` | BibTeX entries for all sources present in the canonical release. |

## Changes In This Release

- Initial public CUSP release.

## Citation Notes

- The canonical dataset file is `cusp_v1.0.csv`.
- The master bibliography file is `cusp_sources_v1.0.bib`.
- To extract only the entries you need from a filtered CUSP table, run:

```bash
python -m cusp.citations --input path/to/your_cusp_table.csv --output references.bib
```
