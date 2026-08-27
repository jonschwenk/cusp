# Aggregation Validation

## Scope

This document records the latest validated rebuild of the default `30m`
aggregation workflow from the canonical observation-level table. The current
snapshot was rebuilt on 2026-08-27 from all 79,389 working observation rows.
The `30m` aggregation is a reproducible derivative, not an official versioned
release artifact for v1.

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
- within each spatial cell-year group, starts a new temporal group when the
  gap between consecutive sorted dates exceeds `31` days
- uses single-linkage, so a chain of qualifying gaps can span more than `31`
  or `62` days even though each consecutive gap remains within the threshold
- aggregates across sources rather than restricting to within-source groups

## Current Rebuild Snapshot

- `aggregated_30m.csv`
  - rows: `34,462`
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
    - `quality_flags`
    - `aggregated_sources`
    - `n_grouped`
- `aggregated_30m_membership.csv`
  - rows: `79,389`
  - unique aggregated groups: `34,462`
  - unique member observations: `79,389`
- `aggregated_30m_excluded_rows.csv`
  - rows: `0`
- `aggregated_30m_qc_flags.csv`
  - rows: `1,538`
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
- `quality_flags` contains the sorted union of member observation flags.
- `aggregated_sources` records the unique contributing `source` values for each
  aggregated row as a comma-delimited list so downstream users can trace
  citation provenance.

## Current QC Flag Counts

- `multi_date_window`: `683`
- `mixed_method`: `381`
- `mixed_pf_observed`: `291`
- `mixed_source`: `183`

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

The rebuilt aggregation and its membership table passed
`python -m cusp.qc validate-aggregated` with no hard-gate failures.

## Confirmed CRS Behavior

No open CRS decision remains for v1:

- aggregation distance is computed in projected `EPSG:3413`
- exported geometries remain in user-facing `EPSG:4326`
