# Observation Build Validation

## Scope

This page records the latest validated state of the observation-level CUSP
build. The current snapshot was generated on 2026-08-06 after standardizing
dense GPR sampling, resolving the Moore/Jafarov overlap, enforcing explicit
observation limits for instrument-based permafrost-absence rows, and restoring
the flagged visual Koyukuk classifications.

Commands used:

```bash
python -m cusp.generate_process_script_metadata --check --strict
python -m cusp.build
python -m cusp.qc validate-observations --out outputs/qc_tests
python -m cusp.qc audit-observations --out outputs/qc_audit
python -m pytest -q
```

The final build and tests were run under Python 3.13.

## Current Snapshot

- canonical observations: `79,389` rows and `12` columns
- included sources: `57`
- date range: `1952-06-01` through `2024-10-11`
- permafrost observed: `62,135`, including `114` visually interpreted rows
- permafrost not detected to a positive observation limit: `17,054`
- visually interpreted permafrost absence without a point-specific observation
  limit: `200`
- all-fields observations: `79,389` rows
- source metadata and source-reference crosswalk: `57` rows each
- hard-deleted input rows: `55`
- build-level QC flag rows: `0`

The 55 hard deletions comprise 39 rows without coordinates and 16 exact
duplicates across the required observation fields. The deletion log preserves
their source rows and reasons.

## Validation Results

All hard gates passed:

- exact canonical schema
- present and unique `cusp_obs_id`
- binary `pf_observed`
- supported observation method codes
- present, globally valid coordinates
- parseable, in-range dates
- nonnegative depth fields
- no zero observation limits

Additional build invariants also passed:

- every instrument-based `pf_observed = 0` row has a positive `obs_limit`
- the only absence rows without `obs_limit` are 200 Koyukuk visual polygon
  classifications, all explicitly marked `VI`
- every absence row has blank canonical `pf_depth` and `thaw_depth`
- every depth-bounded absence row carries the lower-bound flag `LB`
- every presence row without an exact depth carries the upper-bound flag `UB`
- all 57 processing-script metadata headers are valid structured TOML
- normalized coordinate/date/state/depth/method matching found no remaining
  exact cross-source duplicate groups

## Dense GPR Review

CUSP now represents native dense GPR picks at one mean observation per occupied
5 m by 5 m projected cell within each source/site/date survey.

| Source | Native GPR picks | CUSP GPR rows | Spacing |
|---|---:|---:|---:|
| `Jafarov_2016` | 57,294 | 4,752 | 5 m |
| `Moore_et_al_2025` | 135,297 | 8,178 | 5 m |
| `Patton_2021` | 11,607 | 163 | 5 m |
| `Petrone_etal_2016` | 1,357 | 590 | 5 m |
| **Total** | **205,555** | **13,683** | **5 m** |

Jafarov is retained as the original source for the 2013 Barrow campaign. Before
Moore aggregation, the Moore processor removes 57,294 copied Jafarov GPR picks
and 1,297 copied probe observations. It does not use Moore's conflicting 2014
or 2018 dates to identify those copies. Patton and Petrone were checked against
the retained GPR sources and found to have distinct footprints.

Different survey dates and thaw years remain separate even where coordinates
overlap. Spatial overlap by itself is not treated as duplication.

## Nonblocking Diagnostics

The audit reports no rows where `thaw_depth > pf_depth`. This remains a
diagnostic because source definitions can make the two fields non-equivalent.

There are 9,409 rows without `site_id`: 9,308 from `Pawley_2018`, 56 from
`Koyukuk_2018`, and 45 from `Douglas_Koyukuk_2022`. Coordinates are present,
and missing source identifiers remain warning-level rather than a hard gate.

The `Pastick` crosswalk entry identifies the source as an unpublished
compilation and records the limits of its component-level attribution.
Bonnaventure links to the 2026 paper and notes that CUSP's point file was
shared directly rather than distributed with the publication.

Koyukuk contains 56 retained direct field observations and 314 retained points
sampled from visually interpreted permafrost/non-permafrost polygons. The
visual rows carry `VI`, have no point-specific depth or observation limit, and
can be removed as a group for instrument-only or depth-bounded analyses.

## Verdict

The canonical observation table is structurally sound and suitable for the
v1.1 data release. The official release bundle omits derived environmental
features; users can generate those separately with the feature-sampling
workflow.
