# Rebuild CUSP

The rebuild path starts from the repository root and the `cusp` conda
environment.

```bash
conda activate cusp
python -m cusp.build
python -m cusp.qc validate-observations
```

That rebuilds and validates the canonical observation table in `data/`.
The build and QA commands both enforce the machine-readable frozen schema in
`cusp/canonical_observation_schema.json`.

Validate the maintained source-processing metadata without modifying it:

```bash
python -m cusp.generate_process_script_metadata --check --strict
```

Check mode fails if `PROCESS_SCRIPT_METADATA.csv` is stale and never rewrites
the file.

## Optional Derived Workflows

Aggregation is reproducible but not part of the official versioned release
bundle:

```bash
python -m cusp.aggregate
python -m cusp.qc validate-aggregated
```

Feature sampling requires Google Earth Engine authentication and a project your
account can use:

```bash
python -m cusp.features \
  --input exports/latest/cusp_v1.1.csv \
  --output runs/examples/cusp_v1.1_features.csv \
  --manifest runs/examples/cusp_v1.1_features_manifest.json \
  --gee-project <your-earth-engine-project> \
  --resume
```

## Release Gate

The release gate runs the main checks in one place:

```bash
python -m cusp.release_gate --version 1.1 --skip-feature-export --skip-gee-smoke
```

The official data bundle does not include an environmental feature table, so
the release gate skips both feature export and the live Earth Engine smoke
test. Feature sampling remains available as an optional derived workflow.

## Reproducibility Notes

The release build is reproducible from the processed source tables committed
to the repository. Re-creating every processed source table from its earliest
raw input is a different scope: some processors require manual steps, files
that are too large for GitHub, or external services and data. Those
requirements are recorded per source in `PROCESS_SCRIPT_METADATA.csv` and are
described in [External data sources](external-data-sources.md).

For exact historical bytes, checksums, and citations, use the complete snapshot
under `exports/archived/vX.Y/`. Rebuilding from the current source tree creates
the current dataset state, not an earlier release.
