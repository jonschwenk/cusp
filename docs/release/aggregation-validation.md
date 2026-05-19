# Aggregation Validation

## Scope

This document records the first rebuild of the default `30m` aggregation
workflow from the canonical observation-level table. The `30m` aggregation is a
reproducible derivative, not an official versioned release artifact for v1.

Artifacts produced by `python -m cusp.aggregate`:

- `data/aggregated_30m.csv`
- `data/aggregated_30m_membership.csv`
- `data/aggregated_30m_qc_flags.csv`
- `data/aggregated_30m_excluded_rows.csv`
- `data/aggregated_30m.gpkg`
- `data/aggregated_30m_manifest.json`

## Current Default Aggregation Behavior

The current aggregation path:

- reads CUSP observation rows from the working observation table
- requires deterministic `cusp_obs_id` values from the observation build
- assigns observations to deterministic projected grid cells in `EPSG:3413`
- exports the public aggregated artifacts back out in `EPSG:4326` / WGS84 where
  geometry is written
- uses a `30 m` cell size for the default `30m` workflow
- separates aggregation groups by calendar year
- within each spatial cell-year group, links observations into temporal groups
  using a symmetric `31`-day forward/backward rule
- this corresponds to a `62`-day total temporal window, implemented as a
  `31`-day linkage threshold between neighboring observations in the same
  cell-year sequence
- aggregates across sources rather than restricting to within-source groups

## Current Rebuild Snapshot

- `aggregated_30m.csv`
  - rows: `18,412`
  - columns:
    - `cusp_30m_id`
    - `year`
    - `date`
    - `lat`
    - `lon`
    - `pf_observed`
    - `thaw_depth`
    - `pf_depth`
    - `obs_limit`
    - `method`
    - `aggregated_sources`
    - `n_grouped`
- `aggregated_30m_membership.csv`
  - rows: `239,704`
  - unique aggregated groups: `18,412`
  - unique member observations: `239,704`
- `aggregated_30m_excluded_rows.csv`
  - rows: `0`
- `aggregated_30m_qc_flags.csv`
  - rows: `1,346`
- `aggregated_30m.gpkg`
  - CRS: `EPSG:4326`

## Output Semantics

- `cusp_30m_id` is deterministic and derived from the sorted set of member
  `cusp_obs_id` values.
- `year` is explicit in the output even though the public-facing artifact name
  is `30m`.
- `date` is currently the latest observation date within the aggregated
  spatial-temporal group.
- `pf_observed` is currently the mean of the retained `0/1` observations,
  so mixed groups yield fractional values between `0` and `1`, while retaining
  the field name `pf_observed`.
- `method` is preserved when all retained observations in the group share one
  method value; heterogeneous groups are labeled `mixed`, while truly unknown
  source-level methods can still remain `unknown`.
- `aggregated_sources` records the unique contributing `source` values for each
  aggregated row so downstream users can trace citation provenance.

## Current QC Flag Counts

- `mixed_pf_observed`: `612`
- `mixed_method`: `329`
- `multi_date_window`: `309`
- `mixed_source`: `96`

These are audit outputs, not automatic blockers.

## Interpretation Notes

The current temporal rule is meant to prevent observations from very different
parts of the thaw season from collapsing together just because they share a
location-year cell.

This means the aggregation product is not a simple "all observations within 30
m and year" collapse. It is a spatial-plus-temporal aggregation intended to be
more suitable for active-layer style modeling and comparison workflows.

## Legacy Artifact Cleanup

The old legacy aggregation CSVs have now been removed from the repo:

- `aggregated_10000m_noyear.csv`
- `aggregated_1000m_year.csv`
- `aggregated_100m_year.csv`
- `aggregated_30m_year.csv`
- `aggregated_5000m_year.csv`
- `aggregated_500m_noyear.csv`

## Remaining Questions To Confirm

No open CRS decision remains for v1:

- aggregation distance is computed in projected `EPSG:3413`
- exported geometries remain in user-facing `EPSG:4326`
