# Aggregation Guide

CUSP contains many observations that are densely sampled in some places and
much sparser elsewhere. Aggregation can be useful when a model assumes more
independent observations, when you want to reduce the influence of dense local
sampling, or when you plan to join CUSP to environmental layers that are much
coarser than individual field points.

The CUSP aggregation tool groups nearby observations within a chosen spatial
and temporal window. The default settings are `30 m` and `31 days`, but you can
set whatever distance and time limits are appropriate for your analysis.

## What Aggregation Does

The aggregation workflow:

- starts from a CUSP observation table
- groups observations that fall in the same projected grid cell and date window
- keeps annual separation so records from different years are not grouped
  together
- allows grouping across sources
- preserves provenance through a membership table
- sets aggregated `pf_observed` to the mean of member `0/1` values
- sets aggregated `method` to `mixed` when multiple methods are present

Important default settings:

| Setting | Default | Meaning |
| --- | ---: | --- |
| Distance threshold | `30 m` | Observations are grouped within projected 30 m grid cells unless you pass a different `--distance-m` value. |
| Temporal linkage | `31 days` | Within the same year and grid cell, observations can be linked when neighboring observation dates are no more than 31 days apart. |
| Effective total window | up to `62 days` | A grouped date can include observations as much as 31 days before and 31 days after the representative date. |
| Annual separation | preserved | Observations from different calendar years are not grouped together. |
| Grouping projection | `EPSG:3413` | Spatial grouping is computed in a projected Arctic coordinate system. |
| Output coordinates | `EPSG:4326` | Aggregated latitude and longitude are exported in WGS84. |

## Run The Default Aggregation

```bash
python -m cusp.aggregate
python -m cusp.qc validate-aggregated
```

## Important Options

See all options with:

```bash
python -m cusp.aggregate --help
```

Common options:

| Option | What it controls |
| --- | --- |
| `--input` | Observation-level table to aggregate. |
| `--output` | Aggregated CSV to write. |
| `--membership-output` | Table linking each original `cusp_obs_id` to an aggregated group. |
| `--flags-output` | QC flags for mixed sources, mixed methods, mixed permafrost labels, and similar checks. |
| `--excluded-output` | Rows skipped by the aggregation workflow. |
| `--gpkg-output` | GeoPackage export of aggregated points. |
| `--manifest-output` | Parameters, row counts, hashes, and run metadata. |
| `--distance-m` | Spatial grouping threshold in meters. The default is `30`. |
| `--temporal-link-days` | Temporal linkage threshold in days. The default is `31`. |

## Example: Custom Aggregation

```bash
python -m cusp.aggregate \
  --input exports/latest/cusp_v1.0.csv \
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
