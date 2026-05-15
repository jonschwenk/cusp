# GEE Feature Sampling

The feature sampler adds environmental information to CUSP rows using Google
Earth Engine. You might use this tool when you want model inputs, spatial
context, or comparison variables such as climate, terrain, soils, or surface
water occurrence at CUSP observation locations.

For contributor-oriented instructions on extending the sampler, see
[Adding new GEE features](../contributing/adding-gee-features.md).

## Run Feature Sampling

```bash
python -m cusp.features --input exports/latest/cusp_v1.0.csv
```

The sampler writes:

- a feature table CSV
- a companion JSON manifest describing the feature set, input table, and
  sampling configuration

## Earth Engine Authentication

Feature sampling does not use a CUSP-owned account or checked-in credentials.
Each user should authenticate with their own Google Earth Engine account and
run sampling through a Google Cloud / Earth Engine project they own or have
permission to use.

One-time local setup:

```bash
earthengine authenticate
```

Then pass the project explicitly when sampling:

```bash
python -m cusp.features \
  --input exports/latest/cusp_v1.0.csv \
  --output runs/examples/cusp_v1.0_features.csv \
  --manifest runs/examples/cusp_v1.0_features_manifest.json \
  --gee-project <your-earth-engine-project> \
  --resume
```

Internally, the sampler calls `ee.Initialize(project=<your-earth-engine-project>)`.
If a user has configured a default Earth Engine project outside CUSP, they can
omit `--gee-project`, but passing it explicitly is clearer and more
reproducible.

## Input Tables

The sampler can read any point-like CUSP table that includes:

- a canonical join ID:
    - `cusp_obs_id` for observation-level tables such as `cusp_vX.Y.csv`
    - `cusp_30m_id` for aggregated tables such as `aggregated_30m.csv`
- `lat`
- `lon`
- either `date` or `year`

For a released feature table, use the observation-level CUSP table so the
result is keyed to `cusp_obs_id`.

## Current Base Feature Set

`base_v1` is the default set of environmental features sampled when you do not
request a custom feature list.

| Feature family | Output columns | What it represents |
| --- | --- | --- |
| `soil_texture` | `sand`, `silt`, `clay` | Depth-weighted SoilGrids texture fractions |
| `soil_oc` | `soil_oc` | Depth-weighted SoilGrids soil organic carbon |
| `climate` | `temperature`, `precip` | Antecedent ERA5 temperature and annualized precipitation |
| `swo_landsat` | `swo_landsat` | Long-term Landsat surface-water occurrence |
| `merit_hand` | `merit90_hand` | Height above nearest drainage |
| `terrain` | `slope`, `aspect`, `curvature_6m`, `curvature_10m`, `curvature_14m`, `curvature_18m` | ArcticDEM terrain derivatives |

## Feature Sources

| Feature(s) | Earth Engine source | Native resolution | Temporal handling |
| --- | --- | --- | --- |
| `slope`, `aspect`, `curvature_*` | `UMN/PGC/ArcticDEM/V4/2m_mosaic` | 2 m mosaic | Static |
| `sand`, `silt`, `clay` | `projects/soilgrids-isric` | 250 m | Static |
| `soil_oc` | `projects/soilgrids-isric/soc_mean` | 250 m | Static |
| `temperature` | `ECMWF/ERA5/MONTHLY` | about 31 km | 20-year antecedent mean through the observation year |
| `precip` | `ECMWF/ERA5/MONTHLY` | about 31 km | 20-year antecedent mean through the observation year, rescaled to annual precipitation |
| `swo_landsat` | `JRC/GSW1_4/MonthlyHistory` | 30 m | 1999-2021 occurrence window |
| `merit90_hand` | `MERIT/Hydro/v1_0_1` | about 90 m | Static |

If a temporal feature only partially overlaps the requested time window, the
sampler uses the available overlap. If there is no overlap, it writes `NaN`.

## Sampling Defaults

| Setting | Default |
| --- | --- |
| Sampling mode | direct point sampling |
| Sampling scale | resolved from each Earth Engine image's native projection at runtime |
| Optional sampling buffer | off unless `--sample-buffer-m` is set |
| Chunk size | `5000` rows per Earth Engine request block |
| Curvature method | `LoG` |
| Curvature window sizes | `3`, `5`, `7`, `9` |
| Curvature sigma | `1.0` |
| Climate averaging window | `20 years` |

The sampler writes the output CSV and manifest after each completed feature
family. If a long run is interrupted, rerun the same command with `--resume` to
skip feature columns that are already present in the output.

## Transform And Null Handling

The sampler does not perform model-oriented imputation or scaling. Missing
sampled values remain null/`NaN` in the feature table.

Current derived-feature behavior:

- SoilGrids texture outputs are depth-weighted sand, silt, and clay fractions.
- SoilGrids organic carbon is depth-weighted across depth bands.
- ERA5 temperature is a 20-year antecedent monthly mean through the observation
  year.
- ERA5 precipitation is sampled from monthly total precipitation, averaged over
  the antecedent window, and multiplied by `12` to express an annualized value.
- JRC Global Surface Water monthly classes are converted to a 1999-2021 water
  occurrence percentage.
- Terrain curvature is derived from ArcticDEM elevation with the configured
  Laplacian-of-Gaussian settings and window sizes.

## Output Design

The feature table keeps the canonical join column plus standard point identity
fields when available:

- canonical ID column
- `date`
- `year`
- `lat`
- `lon`
- sampled features

This keeps the feature table joinable without forcing users to carry the full
observation or aggregation table around while exploring models.

## Why Buffering Is Optional

Earth Engine can sample points directly, and that is the default behavior.

An optional sampling buffer still exists because some environmental layers may
benefit from neighborhood summaries rather than exact point intersections, for
example:

- coarse-resolution climate or water layers
- slight point-location uncertainty relative to raster resolution
- use cases where a local mean is more meaningful than one intersecting pixel

## Adding Features

To add your own feature or propose a new default feature for CUSP, see
[Adding new GEE features](../contributing/adding-gee-features.md).

## Current Limitations

- routine tests cover package behavior, registry resolution, input
  normalization, and output joins
- the release gate can run a small live Earth Engine smoke test when
  `--gee-project` is supplied
- Landsat spectral bundles are not yet part of `base_v1`
- the sampler assumes the CUSP conda environment has `earthengine-api`,
  `geemap`, and `geopandas` available
