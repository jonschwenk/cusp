# CUSP Release v1.2

## Summary

- Dataset version: `v1.2`
- Code version: `0.1`
- Git commit: `b9658423d16978f42b6153e12c5fd47f6c482c65`
- Generated at (UTC): `2026-10-05T18:56:08.096164+00:00`
- Canonical rows: `80264`
- Included sources: `60`
- Date range: `1952-06-01` to `2025-02-01`
- Feature export: not included

## Exported Artifacts

| File | Rows | Size (bytes) | SHA-256 | Note |
|---|---:|---:|---|---|
| `cusp_v1.2.csv` | 80264 | 9158084 | `76a6c1365ec75c719f3881d0ff834c541166acfe9f114cc69087050c328523f9` | Canonical CUSP dataset. |
| `cusp_sources_v1.2.bib` | 60 | 23865 | `f4ee7eb1ef89a7d96b844266bb73dc94efcb8bf6073e5ab5fafeb2bb9c8243ff` | BibTeX entries for all sources present in the canonical release. |

## Changes In This Release

Released on 2026-10-05 as a complete observation-level snapshot:
**80,264 observations from 60 sources**, covering 1952-06-01 to 2025-02-01.
This is a net addition of **875 observations and three sources** over v1.1.

- Added 437 CALM-South annual observations, including 11 depth bounds, from
  the original public workbook. These extend CUSP into the Southern Hemisphere.
- Added 214 Northern Hemisphere annual observations from Streletskiy et al.
  (2026). Retained existing original CALM, PERMOS, and CALM-South records instead
  of their synthesis copies; excluded unresolved depth conflicts and ambiguous
  zeros. Available synthesis records do not require contacting each provider.
- Added ten exact-date Crater Lake manual probes from the public A-ERT archive.
  These use representative site coordinates (`CS`) and overlap flags (`DO`)
  because they overlap CALM-South annual grid summaries; they are not independent
  evidence of site-year conditions. No ERT-derived depths were ingested.
- Fixed the Pastick overlap filter's handling of repeated DataFrame indices,
  restoring 214 canonical observations wrongly excluded alongside the 58
  intended NCSS matches. One additional restored source row is an exact
  duplicate and remains excluded by the canonical build.
- Preserved every v1.1 observation, field value, and observation ID. The frozen
  12-column contract, units, method codes, and ID algorithm are unchanged.
- Updated source attribution, processing metadata, executable documentation,
  and export checks. New exports use LF line endings for reproducible checksums
  across Windows and Unix checkouts. Environmental features and aggregations
  remain optional derivatives, not official release assets.
- Preserved the Streletskiy raw CSV's upstream line endings in Git so its
  provenance checksum and processing checks also pass on Linux. No source
  values or released observations change as a result.

### Hosting And Attribution

v1.2 is published on GitHub for the **ARDAC release-sync workflow test**.
No Zenodo deposit or CUSP version DOI is created for this release at this stage.
The planned Zenodo archive migration is deferred until partner testing is done.

Cite CUSP v1.2 and every original data source used in your analysis. Keep the
version-matched bibliography and `RELEASE_INFO.md`, which records the build
commit, counts, and SHA-256 checksums. Published historical v1.0 and v1.1
GitHub releases are unchanged.

## Citation Notes

- The canonical dataset file is `cusp_v1.2.csv`.
- The master bibliography file is `cusp_sources_v1.2.bib`.
- To extract only the entries you need from a filtered CUSP table, run:

```bash
python -m cusp.citations --input cusp_v1.2.csv --master-bib cusp_sources_v1.2.bib --output references.bib
```

Run from the downloaded bundle directory. For a study, replace `--input` with your final filtered table.
