# Rebuild And Processing Commands

These examples show common CUSP commands. They are most useful if you want to
rebuild the dataset, make spatial summaries, or sample environmental
information on your own computer.

If you only want to use the released data, start with
[Release products](../getting-started/release-products.md).

They assume you are running from the repository root with the `cusp`
environment activated:

```bash
conda activate cusp
```

Feature sampling uses your own Google Earth Engine login and project. Before
running feature examples, authenticate once with:

```bash
earthengine authenticate
```

Then pass a Google Cloud / Earth Engine project that your account can use as
`--gee-project <your-earth-engine-project>`.

The examples below use `exports/latest/cusp_v1.0.csv` as the input release
file. Replace that with the path to the CUSP release file you downloaded or
exported.

## Generate An Aggregated Derivative

The default aggregation is:

```bash
python -m cusp.aggregate
python -m cusp.qc validate-aggregated
```

To create a custom `100 m` aggregation under `runs/examples/`:

The main aggregation knobs are:

- `--input`: the observation-level table to aggregate. In the repository build
  workflow, this is the working observation table under `data/`.
- `--distance-m`: projected grid-cell size in meters. The default is `30`;
  the commands below use `100`.
- `--temporal-link-days`: maximum day gap used to link neighboring
  observations within the same grid cell and calendar year. The default
  release behavior uses `31`, which creates a symmetric seasonal linkage
  window without merging the whole year into one group.
- `--output`: the aggregated point table. This is the main table most users
  inspect or model with.
- `--membership-output`: row-level provenance mapping every contributing
  `cusp_obs_id` to its aggregated group.
- `--flags-output`: diagnostic flags such as mixed methods, mixed permafrost
  labels, multiple source contributions, or multi-date windows.
- `--excluded-output`: observations skipped by the aggregation workflow.
- `--gpkg-output`: geospatial export of the aggregated points.
- `--manifest-output`: row counts, hashes, parameters, and generation metadata
  for the run.

```bash
python -m cusp.aggregate \
  --input exports/latest/cusp_v1.0.csv \
  --output runs/examples/aggregated_100m_example.csv \
  --membership-output runs/examples/aggregated_100m_example_membership.csv \
  --flags-output runs/examples/aggregated_100m_example_qc_flags.csv \
  --excluded-output runs/examples/aggregated_100m_example_excluded_rows.csv \
  --gpkg-output runs/examples/aggregated_100m_example.gpkg \
  --gpkg-layer aggregated_100m_example \
  --manifest-output runs/examples/aggregated_100m_example_manifest.json \
  --distance-m 100 \
  --temporal-link-days 31

python -m cusp.qc validate-aggregated \
  --input runs/examples/aggregated_100m_example.csv \
  --membership runs/examples/aggregated_100m_example_membership.csv
```

The same custom aggregation can be written with PowerShell variables if you
prefer:

```powershell
$DistanceM = 100
$TemporalLinkDays = 31
$InputPath = "exports\latest\cusp_v1.0.csv"
$OutDir = "runs\examples"
$Stem = "aggregated_${DistanceM}m_example"

New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

python -m cusp.aggregate `
  --input $InputPath `
  --output "$OutDir\$Stem.csv" `
  --membership-output "$OutDir\${Stem}_membership.csv" `
  --flags-output "$OutDir\${Stem}_qc_flags.csv" `
  --excluded-output "$OutDir\${Stem}_excluded_rows.csv" `
  --gpkg-output "$OutDir\$Stem.gpkg" `
  --gpkg-layer $Stem `
  --manifest-output "$OutDir\${Stem}_manifest.json" `
  --distance-m $DistanceM `
  --temporal-link-days $TemporalLinkDays

python -m cusp.qc validate-aggregated `
  --input "$OutDir\$Stem.csv" `
  --membership "$OutDir\${Stem}_membership.csv"
```

## Sample Features On An Aggregated Table

For a quick live smoke test on the aggregation created above:

The main feature-sampling knobs are:

- `--input`: any point-like CUSP table with `lat`, `lon`, date/year
  information, and a canonical ID such as `cusp_obs_id` or `cusp_30m_id`.
- `--output`: feature table CSV. The output keeps the ID, coordinates, date/year
  fields, and sampled feature columns.
- `--manifest`: metadata for the feature run, including selected feature
  families, source collections, and sampling settings.
- `--gee-project`: Earth Engine project used for authentication and quota.
- `--feature-set none`: disables the default `base_v1` set so a smoke test can
  request only the feature names passed through `--features`.
- `--features`: comma-separated feature families to sample. `soil_oc` and
  `merit_hand` are useful smoke-test choices because they are static and quick
  compared with climate or surface-water history.
- `--resume`: reuses completed columns already present in the output CSV and
  continues missing feature families. This is recommended for any non-trivial
  Earth Engine run.

```bash
python -m cusp.features \
  --input runs/examples/aggregated_100m_example.csv \
  --output runs/examples/aggregated_100m_example_features.csv \
  --manifest runs/examples/aggregated_100m_example_features_manifest.json \
  --gee-project <your-earth-engine-project> \
  --feature-set none \
  --features soil_oc,merit_hand \
  --resume
```

To sample the full `base_v1` feature set on that same aggregation:

```bash
python -m cusp.features \
  --input runs/examples/aggregated_100m_example.csv \
  --output runs/examples/aggregated_100m_example_base_v1_features.csv \
  --manifest runs/examples/aggregated_100m_example_base_v1_features_manifest.json \
  --gee-project <your-earth-engine-project> \
  --resume
```

PowerShell users can run the smoke feature example with:

```powershell
$GeeProject = "<your-earth-engine-project>"
$InputPath = "runs\examples\aggregated_100m_example.csv"
$OutDir = "runs\examples"
$Stem = [System.IO.Path]::GetFileNameWithoutExtension($InputPath)

python -m cusp.features `
  --input $InputPath `
  --output "$OutDir\${Stem}_features.csv" `
  --manifest "$OutDir\${Stem}_features_manifest.json" `
  --gee-project $GeeProject `
  --feature-set none `
  --features soil_oc,merit_hand `
  --resume
```

## Feature Table For A Release

Aggregated feature tables are useful for modeling and exploration, but they are
different from the release feature table.

The release feature table is sampled from the rebuilt observation table in the
repository:

```bash
python -m cusp.features \
  --input exports/latest/cusp_v1.0.csv \
  --output runs/examples/cusp_v1.0_features.csv \
  --manifest runs/examples/cusp_v1.0_features_manifest.json \
  --gee-project <your-earth-engine-project> \
  --resume
```

This output is keyed to `cusp_obs_id` and can be packaged as
`cusp_features_vX.Y.csv` with `python -m cusp.export`.
