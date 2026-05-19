# Observation Build Validation

## Scope

This document records a manual QA pass on the rebuilt observation-level
artifacts:

- the working observation table exported later as `cusp_vX.Y.csv`
- the internal all-fields review table
- the internal source-summary table
- the internal source-reference crosswalk

The goal of this pass was to validate that the current observation-build path
produces a structurally sound observation-level release candidate before any
aggregation work begins.

## Environment

- combine rebuild executed in `cusp2`
- validation queries executed in `cusp2`
- source-processing layer treated as the current accepted input set, with
  deferred sources still excluded from the release set

## Current Rebuild Snapshot

- working observation table
  - rows: `249,012`
  - columns: `11`
  - unique sources: `50`
  - date range: `1961-09-01` to `2024-10-03`
- internal all-fields review table
  - rows: `249,012`
  - preserves source-specific/wide fields for provenance and review
- internal source-summary table
  - rows: `50`
  - unique sources: `50`
- internal source-reference crosswalk
  - rows: `50`
  - one row per included source
  - filtered from `cusp_sources_bibtex.csv` to the current included-source set
- internal observation release manifest
  - generated from the build path
  - includes row counts, source counts, date range, file sizes, hashes, and
    generation timestamp for the observation-level artifacts

## Checks That Passed

- required observation-level columns are present in the working observation
  table
- the working observation table now contains only the canonical
  observation-level fields:
  - `cusp_obs_id`
  - `source`
  - `site_id`
  - `lat`
  - `lon`
  - `date`
  - `pf_observed`
  - `thaw_depth`
  - `pf_depth`
  - `obs_limit`
  - `method`
- `cusp_obs_id` is now present, non-null, and unique across the canonical
  observation table
- `pf_observed` contains only `0` and `1` when non-null
- dates are parseable across the full table
- longitude and latitude ranges are within global bounds
- source coverage matches the current included-source set
- the working observation table and internal source-summary table rebuild deterministically in the audited
  environment
- the source-reference crosswalk rebuilds cleanly and has one unique row per
  included `source`
- the observation release manifest is now generated automatically by
  `build.py`

## Findings That Need Cleanup Before Release

### 1. A small number of citation metadata fields still need cleanup in the
source-reference crosswalk

The crosswalk itself is structurally correct, but two sources still need
citation metadata attention:

- `Bonaventure_Whati`: missing `title`
- `Pastick`: currently missing `author`, `year`, and `title`

These are documentation/citation cleanup items rather than observation-build
failures, but they should be resolved before treating the crosswalk as
release-ready.

### 2. A small number of records are still deleted for missing coordinates

The canonical observation table has no missing coordinates after hard deletion.
Current missing-coordinate deletion-log records are concentrated in a few
sources:

- `Minsley_2015`: `15`
- `Zhao_2021`: `12`
- `Hollingsworth_2005`: `6`
- `Ruess_2025`: `6`

These do not look like widespread combine failures; they appear to be
source-specific metadata gaps. They should be reviewed source by source and
either:

- filled from source materials,
- explicitly accepted as coordinate-missing records, or
- excluded from the public observation-level release if coordinates are deemed
  required.

### 3. A small number of records still have missing `site_id`

Missing `site_id` values are concentrated in:

- `Pawley_2018`: `9308`
- `Bonaventure_Whati`: `145`
- `Koyukuk_2018`: `56`
- `Douglas_Koyukuk_2022`: `45`
- `Brown_etal_2000_calm`: `38`

`Pawley_2018` is expected to have missing `site_id` values because the source
does not provide row-level site identifiers, and the processing script does not
assign synthetic IDs.

## Findings That Look Diagnostic Rather Than Blocking

### Duplicate-key groups are common in a few sources

Using the key:

- `source`
- `site_id`
- `date`
- `lat`
- `lon`

there are `14,999` rows participating in duplicate-key groups. These are
dominated by:

- `Brown_etal_2000_calm`
- `Natali_2023`
- `Jafarov_2016`
- `Bakian_Dogaheh_2020`

Inspection suggests these are often repeated observations at the same site/date
or multiple values recorded under the same site/date identifier, not obviously
accidental duplicated rows introduced by the combine step. This should remain a
diagnostic QA check, but it is not currently being treated as a release blocker
by itself.

### Swapped-coordinate heuristic is almost entirely a `Brown_etal_2000_calm` issue

The simple swapped-lat/lon heuristic flags `442` rows, all from
`Brown_etal_2000_calm`. Given the global historical scope of that source, these
are more likely to be heuristic false positives than actual swapped coordinates.
This should remain an audit output, not an automatic blocker.

### The source summary and source-reference crosswalk serve different roles

The source-summary artifact is a compact per-source QA summary. The
source-reference crosswalk is the citation-facing one-row-per-source artifact
filtered to the included release set.

## Recommended Next Fixes

1. Decide whether missing coordinates are acceptable in the public
   observation-level release.
2. Add stable `site_id` values where feasible, especially for sources where
   the source clearly provides one or a synthetic transect/site identifier is
   appropriate, but treat remaining missing-`site_id` cases as warning-level
   issues rather than release blockers.

## Status After Upstream QA Push

After pushing a substantial amount of QA/QC back into the individual
`process_<source>.py` scripts, the current observation-level build state is much
cleaner:

- no remaining `missing_method` flags
- no remaining unsupported method values in the canonical observation table
- no remaining `zero_obs_limit` flags
- no remaining `(0,0)` coordinate rows in the built observation table
- `missing_site_id` is no longer emitted as a build-level QC flag
- missing `site_id` remains accepted as a non-blocking source-level limitation
  where the original source does not provide one

Current remaining hard deletions are dominated by:

- source-level duplicate groups in `Brown_etal_2000_calm`, `Jafarov_2016`, and
  `Bakian_Dogaheh_2020`
- missing-coordinate rows in `Minsley_2015`, `Zhao_2021`,
  `Hollingsworth_2005`, and `Ruess_2025`

The duplicate-heavy sources are currently deferred for later source-level
review rather than treated as public release blockers.

## Interim Validation Verdict

The rebuilt observation-level bundle is structurally sound and suitable to use
as the basis for continued release cleanup. The remaining issues are no longer
combine-step failures. They are a short list of source-level cleanup items and
citation-metadata gaps that should be resolved before treating the full
observation-level release bundle as final.

## Current Observation Build Behavior

The observation build path is now implemented in `cusp/build.py`.
`cusp/combine_data.py` is now only a compatibility wrapper around that logic.
Its current behavior is:

- rebuild raw all-fields observations from the processed source tables
- normalize `method` into the controlled release vocabulary where possible
- write a canonical working observation table that contains only the required core columns
- write an all-fields table as the wide/provenance-preserving version
- write a source-reference crosswalk as the one-row-per-source citation
  mapping artifact
- write an observation release manifest as the observation-level artifact
  inventory and checksum manifest
- delete rows with:
  - missing coordinates
  - missing `pf_observed`
  - `(0,0)` coordinates
  - exact duplicates across the canonical required fields
- write a deletion log to record hard deletions and reasons
- write a QC flag log to record non-deletion issues such as:
  - missing `method`
  - `obs_limit = 0`

The current build assumption is that missing `site_id` is acceptable in the
canonical observation table, but missing coordinates and missing `pf_observed`
are not.

## QA/QC Boundary

The intended long-term boundary is:

- `process_<source>.py` handles source-specific interpretation, source-level QA,
  sentinel handling, units, date assumptions, and within-source deduplication
- `build.py` handles cross-source consistency, canonical output shaping, global
  duplicate detection, and explicit release deletion/flag logs

This means contributor pull requests should ideally arrive with source-level
judgment already encoded in the processing script, rather than relying on the
final observation build step for source-specific interpretation.
