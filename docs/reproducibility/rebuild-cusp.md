# Rebuild CUSP

The rebuild path starts from the repository root and the `cusp` conda
environment.

```bash
conda activate cusp
python -m cusp.build
python -m cusp.qc validate-observations
```

That rebuilds and validates the canonical observation table in `data/`.

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
python -m cusp.features --input exports/latest/cusp_v1.1.csv --gee-project <your-earth-engine-project>
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

Some original source inputs are too large or too awkward to store directly in
GitHub. Those cases are documented in
[External data sources](external-data-sources.md).
