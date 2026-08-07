# CUSP Versioning and Exports

## Goal

Make every official CUSP data release:

- citable
- reproducible
- easy to find as the current `latest`
- easy to recover later as an archived historical snapshot

## Release Model

CUSP dataset versions are independent of the Python package version. A data
release records the accepted observations and their source bibliography; it
does not imply a software release.

The canonical bundle contains the observation-level dataset, the bibliography
for included sources, and a release record with checksums. Aggregation and
environmental feature sampling remain supported derived workflows, but their
outputs are not canonical release artifacts.

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
- release citation coverage changes because the included source set changed

## Official Export Layout

Use a real export tree inside the repo workspace:

```text
exports/
  latest/
    cusp_v1.1.csv
    cusp_sources_v1.1.bib
    RELEASE_INFO.md
  archived/
    v1.0/
      ...
    v1.1/
      cusp_v1.1.csv
      cusp_sources_v1.1.bib
      RELEASE_INFO.md
```

Notes:

- the export bundle is intentionally flat
- aggregation outputs are not part of the official versioned export bundle

## Official Exported Files

The core exported filenames are:

- `cusp_vX.Y.csv`
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

### Historical v1.0 Feature File

The original v1.0 repository bundle included `cusp_features_v1.0.csv`, an
observation-level Google Earth Engine feature table. The retroactive v1.0
GitHub Release preserves that file as part of the historical snapshot.

It is not part of the canonical release contract. Beginning with v1.1, CUSP
releases omit feature tables. Users can generate one from a chosen observation
release with `python -m cusp.features`; the result is a derived product keyed
by `cusp_obs_id`.

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

## Derived Workflows

Aggregation and feature sampling remain reproducible workflows rather than
official versioned release artifacts.

That means:

- `python -m cusp.aggregate` remains available
- `aggregated_30m.csv` remains useful and documented
- `python -m cusp.features` can produce observation- or aggregation-keyed
  environmental tables
- aggregation outputs do not need to be rebuilt and archived for every CUSP
  dataset version unless the team later promotes them back into the official
  release bundle

## Recommended Release Workflow

1. Rebuild the canonical dataset with `python -m cusp.build`.
2. Validate processing metadata and the canonical observation table.
3. Decide the next dataset version.
4. Run the scripted release gate, including strict docs validation, with
   `python -m cusp.release_gate --version 1.1 --skip-feature-export --skip-gee-smoke`.
5. Package the official bundle with `python -m cusp.export` and no
   `--features-input` argument. Official exports also refresh the generated
   release tracker in `README.md` from `exports/latest/cusp_vX.Y.csv`.
6. Review `RELEASE_INFO.md`, file hashes, and row/source counts.
7. Commit the archived bundle, refresh `exports/latest/`, tag the data version,
   and publish the matching GitHub Release.

The release gate writes test exports and aggregation outputs under
`runs/release_gate/`. Those files validate the workflow but are not official
release artifacts.

The README tracker can also be refreshed or checked directly:

```bash
python -m cusp.readme_tracker
python -m cusp.readme_tracker --check
```

## Current Release Sequence

The existing v1.0 archive is published retroactively as the historical initial
release. The corrected and expanded observation build is published as v1.1.
