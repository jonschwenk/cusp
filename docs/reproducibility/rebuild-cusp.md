# Rebuild CUSP

The rebuild path starts from the repository root and the `cusp` conda
environment.

```bash
conda activate cusp
python -m cusp.build
python -m cusp.qc validate-combined
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
python -m cusp.features --input exports/latest/cusp_v1.0.csv --gee-project <your-earth-engine-project>
```

## Release Gate

The release gate runs the main checks in one place:

```bash
python -m cusp.release_gate --version 1.0 --skip-gee-smoke
```

For a final manual release check, run the same gate with a live Earth Engine
project instead of skipping the smoke test.

## Reproducibility Notes

Some original source inputs are too large or too awkward to store directly in
GitHub. Those cases are documented in
[External data sources](external-data-sources.md). Known source-level
limitations are tracked in
[Reproducibility exceptions](reproducibility-exceptions.md).
