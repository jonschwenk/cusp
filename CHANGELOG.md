# Changelog

All notable changes to the CUSP release surface should be recorded here.

This file is intended to track changes to:

- official data artifacts
- supported build and validation workflows
- supported aggregation workflow behavior
- supported feature-sampling surface
- contributor-facing metadata and release policy

## [Unreleased]

### Added

- supported module entry points for:
  - `python -m cusp.build`
  - `python -m cusp.aggregate`
  - `python -m cusp.qc`
  - `python -m cusp.features`
- deterministic `cusp_obs_id` and `cusp_30m_id`
- canonical observation build outputs:
  - `cusp_observations.csv`
  - `cusp_observations_allfields.csv`
  - `cusp_observations_metadata.csv`
  - `all_sites.gpkg`
  - `source_reference_crosswalk.csv`
- supported `30m` aggregation workflow outputs:
  - `aggregated_30m.csv`
  - membership, QC, excluded-row, GeoPackage, and manifest artifacts
- structured TOML metadata for source-processing scripts
- generated process-script metadata inventory
- supported GEE feature sampler scaffold and `base_v1` feature set
- versioning/export policy in `docs/release/versioning-and-exports.md`
- flat release export packager in `python -m cusp.export`
- citation extraction helper in `python -m cusp.citations`
- resumable feature-sampling checkpoints after each completed feature family
- live feature-sampling progress messages for table loading, Earth Engine
  initialization, chunk completion, and checkpoint writes
- CLI-first examples for generating aggregation derivatives and sampling GEE
  features on aggregated CUSP tables
- contributor guides for:
  - adding new data
  - adding new GEE features
  - running alternate aggregations
  - schema, attribution, and clearance workflow

### Changed

- observation-level release build is now unified around `python -m cusp.build`
- aggregation is now unified around `python -m cusp.aggregate`
- QA validation now lives in the supported `cusp.qc` package
- supported terrain features now use `UMN/PGC/ArcticDEM/V4/2m_mosaic`
- climate feature sampling now handles out-of-coverage years by returning `NaN`
  instead of crashing
- feature sampling now reports progress by feature, year, and chunk
- `base_v1` feature sampling now groups terrain and climate outputs into
  composite Earth Engine requests to reduce interactive sampling overhead

### Removed

- stale legacy aggregated CSVs
- old analysis, collation, resampling, ML-prep, and temp-feature code paths
  from the active repo surface

## Release template

When a real dataset release is cut, add a section like:

```md
## [v1.0] - YYYY-MM-DD

### Added
- ...

### Changed
- ...

### Removed
- ...
```

Recommended release notes should clearly call out:

- newly added or deferred sources
- schema changes
- aggregation behavior changes
- feature-sampler changes that affect supported workflows
