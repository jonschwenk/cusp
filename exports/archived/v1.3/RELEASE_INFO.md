# CUSP Release v1.3

## Summary

- Dataset version: `v1.3`
- Code version: `0.1`
- Git commit: `371a2db0a7eedd2cc52aed3c4e894ba6a45060a7`
- Generated at (UTC): `2026-11-05T15:02:41.362593+00:00`
- Canonical rows: `81237`
- Included sources: `61`
- Date range: `1952-06-01` to `2025-02-01`
- Feature export: not included

## Exported Artifacts

| File | Rows | Size (bytes) | SHA-256 | Note |
|---|---:|---:|---|---|
| `cusp_v1.3.csv` | 81237 | 9287890 | `db5d1007f1127d6b36925ee3e6cd07b008e0be2d64493286157fad8ffa268754` | Canonical CUSP dataset. |
| `cusp_sources_v1.3.bib` | 61 | 24333 | `5f6d40adecf67e41719304bb8e92ce89d38a366b492abf095be7b5c4463530c3` | BibTeX entries for all sources present in the canonical release. |

## Changes In This Release

# CUSP v1.3

Released on 2026-11-05 as a complete observation-level snapshot:
**81,237 observations from 61 sources**, covering 1952-06-01 to 2025-02-01.
This adds **973 Yukon Permafrost Database observations** to v1.2. Every v1.2
observation, canonical field value and observation ID is preserved.

## Yukon observations

The Yukon Geological Survey exports dated 2025-09-21 contribute:

| Observation type | Rows |
|---|---:|
| Explicit dated thaw boundaries | 46 |
| Source-labelled permafrost interval bounds | 129 |
| Additional late-summer frozen-ground bounds | 624 |
| Temperature-derived presence bounds | 170 |
| Bounded non-detections | 4 |
| **Total** | **973** |

These are 969 presence observations and four bounded non-detections. Only the
46 explicit thaw records supply exact depths; the other presence records retain
blank exact-depth fields and upper-bound flags. Late-summer frozen-ground
interpretations carry `PA`. The 170 thermal records at 28 stations require two
consecutive well-covered cold years with documented instrument accuracy;
they carry `TI`, `UB`, `DA` and `SS`, and do not supply interpolated ALT.
Repeated thermal summaries share support between adjacent two-year windows.

Unresolved KZK transcription problems, coordinate conflicts, inconsistent dates
and unknown thermal accuracy remain excluded. Sensitivity-only results are not
part of the release. Stewart Crossing does not meet the thermal inclusion rule.
No provenance-supported cross-source duplicate removal was needed. The 86
retained thermal observations near CALM_C24 in shared monitoring years carry
`DO` for spatial/campaign dependence; different measurement support is retained.

The maintainer approved the reviewed source and documented assumptions for
v1.3 on 2026-11-05. Original provider attribution and the Open Government Licence
- Yukon qualifications remain recorded. The detailed processor, pinned inputs,
row accounting, scientific review and overlap evidence are in
[`data/Yukon_Permafrost_Database`](https://github.com/jonschwenk/cusp/tree/v1.3/data/Yukon_Permafrost_Database).

## Validation and compatibility

The permanent 12-column contract, units and observation-ID algorithm are unchanged.
The release gate checks canonical and aggregation QC, exports and strict docs;
the pytest suite additionally covers the Yukon semantic safeguards and pinned
counts. The processor is byte-reproducible across different Python hash seeds.
Final validation on 2026-11-05 passed the release gate and **133 pytest tests
plus 167 subtests**, with one expected Windows-only Bash-check skip. All 80,264
v1.2 rows, canonical values and IDs were compared directly with v1.3 and preserved.
Historical archives remain byte-identical. The separate Python package version
remains 0.1; v1.3 identifies the dataset snapshot.

## Hosting and attribution

The v1.3 bundle is distributed through GitHub and the repository's immutable
archive and `latest` copy. Zenodo migration remains deferred; this release
does not assign a DOI. Cite CUSP v1.3 and every original source represented in
the data used, retaining the version-matched bibliography and `RELEASE_INFO.md`.

## Citation Notes

- The canonical dataset file is `cusp_v1.3.csv`.
- The master bibliography file is `cusp_sources_v1.3.bib`.
- To extract only the entries you need from a filtered CUSP table, run:

```bash
python -m cusp.citations --input cusp_v1.3.csv --master-bib cusp_sources_v1.3.bib --output references.bib
```

Run from the downloaded bundle directory. For a study, replace `--input` with your final filtered table.
