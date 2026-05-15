# CUSP Versioning and Exports Plan

## Goal

Make every official CUSP data release:

- citable
- reproducible
- easy to find as the current `latest`
- easy to recover later as an archived historical snapshot

## Current Release Model

CUSP now separates:

- the canonical released dataset
- optional released observation-level feature tables
- non-release workflows such as aggregation

That means users should cite and share versioned release files such as
`cusp_v1.0.csv`, while the repository can still keep separate working files for
building and checking the release.

## Version Format

Dataset releases use `vX.Y`.

Examples:

- `v1.0`
- `v1.1`
- `v2.0`

This is intentionally simpler than a `vX.Y.Z` scheme.

## Version-Bump Policy

### Major bump

Use a major bump when the public contract changes in a breaking way.

Examples:

- canonical observation schema changes incompatibly
- official release bundle structure changes in a way users must adapt to
- the meaning of core fields changes incompatibly

### Minor bump

Use a minor bump when official data content or official exported products
change meaningfully without breaking the public contract.

Examples:

- a new source is added to the canonical release
- an existing source is removed or deferred from the official release
- source-processing fixes change rows in `cusp_vX.Y.csv`
- the official observation-level feature table is regenerated with materially
  changed content
- release citation coverage changes because the included source set changed

## Official Export Layout

Use a real export tree inside the repo workspace:

```text
exports/
  latest/
    cusp_v1.0.csv
    cusp_features_v1.0.csv
    cusp_sources_v1.0.bib
    RELEASE_INFO.md
  archived/
    v1.0/
      cusp_v1.0.csv
      cusp_features_v1.0.csv
      cusp_sources_v1.0.bib
      RELEASE_INFO.md
    v1.1/
      ...
```

Notes:

- the export bundle is intentionally flat
- `cusp_features_vX.Y.csv` is included only when an observation-level feature
  table keyed to `cusp_obs_id` is provided
- aggregation outputs are not part of the official versioned export bundle

## Official Exported Files

The core exported filenames are:

- `cusp_vX.Y.csv`
- `cusp_features_vX.Y.csv`
- `cusp_sources_vX.Y.bib`
- `RELEASE_INFO.md`

### `cusp_vX.Y.csv`

This is the canonical public CUSP dataset:

- all accepted processed sources
- integrated into the CUSP release schema
- deduplicated
- QA/QC checked

In repository rebuilds, this file is exported from the working observation
table produced by `python -m cusp.build`.

### `cusp_features_vX.Y.csv`

This is an optional official release artifact when present.

Rules:

- it must be keyed to `cusp_obs_id`
- it must align exactly to the canonical observation release
- aggregation-keyed feature tables are not valid official release artifacts

Internally, this should be produced by sampling features against the main CUSP
observation table, not against a spatial summary.

### `cusp_sources_vX.Y.bib`

This is the master bibliography file for the specific sources included in the
release.

It is a filtered subset of the repo’s master `data/cusp_sources.bib`, not a
copy of every possible source ever considered.

### `RELEASE_INFO.md`

This is the human-readable release record for the bundle.

It should include:

- dataset version
- code version
- git commit
- release date / generation time
- row count
- source count
- date range
- exported artifact list
- checksums
- a short “changes in this release” section

## Citation Model

The public citation model is now intentionally simple:

- export one BibTeX file: `cusp_sources_vX.Y.bib`
- use source keys in the data table as BibTeX entry keys
- provide a helper command to extract only the needed entries from any filtered
  CUSP table

Supported helper:

```bash
python -m cusp.citations --input path/to/your_cusp_table.csv --output references.bib
```

This works with tables that contain either:

- `source`
- `aggregated_sources`

## Aggregation Status

The aggregation workflow remains important, but it is currently a
reproducible example workflow rather than an official versioned release
artifact.

That means:

- `python -m cusp.aggregate` remains available
- `aggregated_30m.csv` remains useful and documented
- aggregation outputs do not need to be rebuilt and archived for every CUSP
  dataset version unless the team later promotes them back into the official
  release bundle

## Recommended Release Workflow

1. Rebuild the canonical dataset with `python -m cusp.build`.
2. If needed, generate an observation-level feature table keyed to
   `cusp_obs_id`.
3. Decide the next dataset version, for example `v1.0` or `v1.1`.
4. Run the scripted release gate, including strict docs validation, with
   `python -m cusp.release_gate --version 1.0 --gee-project <your-earth-engine-project>`.
   For CI or environments without Earth Engine credentials, use
   `--skip-gee-smoke` and treat the live GEE smoke as a manual release check.
5. Package the official bundle with `python -m cusp.export`.
6. Review `RELEASE_INFO.md`.
7. Publish the archived bundle and refresh `exports/latest/`.

The release gate writes test exports and aggregation outputs under
`runs/release_gate/`. Those files validate the workflow but are not official
release artifacts.

## Practical Recommendation Right Now

For the first public release, the official bundle uses:

- `cusp_v1.0.csv`
- `cusp_features_v1.0.csv`
- `cusp_sources_v1.0.bib`
- `RELEASE_INFO.md`

The feature table is included because the full `base_v1` observation-level
feature export has been sampled against the canonical dataset and aligns to
`cusp_obs_id`.
