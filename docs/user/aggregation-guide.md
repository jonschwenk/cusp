# Aggregation Guide

CUSP contains many observations that are densely sampled in some places and
much sparser elsewhere. Aggregation can be useful when a model assumes more
independent observations, when you want to reduce the influence of dense local
sampling, or when you plan to join CUSP to environmental layers that are much
coarser than individual field points.

The CUSP aggregation tool puts observations into projected grid cells, then
links dates within each cell and calendar year. The default settings are
`30 m` cells and a maximum `31`-day gap between consecutive observations, but
you can choose values appropriate for your analysis.

## What Aggregation Does

The aggregation workflow:

- starts from a CUSP observation table
- groups observations that fall in the same projected grid cell
- starts a new temporal group whenever the gap between consecutive dates is
  greater than the linkage threshold
- keeps annual separation so records from different years are not grouped
  together
- allows grouping across sources
- preserves provenance through a membership table
- sets aggregated `pf_observed` to the mean of member `0/1` values
- sets aggregated `method` to `mixed` when multiple methods are present
- carries forward the union of member `quality_flags`

Important default settings:

| Setting | Default | Meaning |
| --- | ---: | --- |
| Distance threshold | `30 m` | Observations are grouped within projected 30 m grid cells unless you pass a different `--distance-m` value. |
| Temporal linkage | `31 days` | Within the same year and grid cell, consecutive observations remain linked when their date gap is no more than 31 days. |
| Total group span | not fixed | The rule is single-linkage: a chain of qualifying date gaps can produce a group spanning more than 31 or 62 days. |
| Annual separation | preserved | Observations from different calendar years are not grouped together. |
| Grouping projection | `EPSG:3413` | Spatial grouping is computed in a projected Arctic coordinate system. |
| Output coordinates | `EPSG:4326` | Aggregated latitude and longitude are exported in WGS84. |

## Run The Default Aggregation

From a CUSP repository checkout, run the default workflow from the repository
root. It reads `data/cusp_observations.csv` and writes the aggregation bundle to
`data/`:

```bash
python -m cusp.aggregate
python -m cusp.qc validate-aggregated
```

The defaults are relative to your current working directory, not to the Python
installation directory. If you installed the tools and downloaded a versioned
release CSV, run the following from the directory containing
`cusp_v1.1.csv`:

```bash
python -m cusp.aggregate \
  --input cusp_v1.1.csv \
  --data-dir cusp_aggregation

python -m cusp.qc validate-aggregated \
  --input cusp_aggregation/aggregated_30m.csv \
  --membership cusp_aggregation/aggregated_30m_membership.csv
```

Explicit input or output paths override the corresponding path derived from
`--data-dir`.

## Important Options

See all options with:

```bash
python -m cusp.aggregate --help
```

Common options:

| Option | What it controls |
| --- | --- |
| `--data-dir` | Directory used for default input and output paths. The default is `./data`. |
| `--input` | Observation-level table to aggregate. |
| `--output` | Aggregated CSV to write. |
| `--membership-output` | Table linking each original `cusp_obs_id` to an aggregated group. |
| `--flags-output` | QC flags for mixed sources, mixed methods, mixed permafrost labels, and similar checks. |
| `--excluded-output` | Rows skipped by the aggregation workflow. |
| `--gpkg-output` | GeoPackage export of aggregated points. |
| `--manifest-output` | Parameters, row counts, hashes, and run metadata. |
| `--distance-m` | Spatial grouping threshold in meters. The default is `30`. |
| `--temporal-link-days` | Temporal linkage threshold in days. The default is `31`. |

The output `date` is the latest member date in each group. Because grouping is
based on consecutive date gaps, `--temporal-link-days` is not a symmetric
window around that output date and does not impose a hard maximum group span.

## Example: Custom Aggregation

```bash
python -m cusp.aggregate \
  --input exports/latest/cusp_v1.1.csv \
  --output runs/examples/aggregated_100m_example.csv \
  --membership-output runs/examples/aggregated_100m_example_membership.csv \
  --flags-output runs/examples/aggregated_100m_example_qc_flags.csv \
  --excluded-output runs/examples/aggregated_100m_example_excluded_rows.csv \
  --gpkg-output runs/examples/aggregated_100m_example.gpkg \
  --manifest-output runs/examples/aggregated_100m_example_manifest.json \
  --distance-m 100 \
  --temporal-link-days 14
```

If you publish or share a custom aggregation, name it clearly so other users can
distinguish it from the original CUSP release table.

## When To Use Custom Aggregation

Custom aggregation runs are useful for:

- sensitivity analysis
- testing alternate model input density
- evaluating different spatial thinning choices
- matching the approximate scale of environmental covariates
- comparing how temporal linkage changes grouped records

They are user-created derivatives unless they are explicitly published as CUSP
release files.

## Check A Custom Run

For non-default outputs, inspect at least:

- row count
- `n_grouped`
- fraction of mixed-method groups
- fraction of mixed-source groups
- whether grouped points look spatially reasonable

You may also want to re-sample environmental features for the aggregated table.
See [GEE feature sampling](feature-sampling.md).
