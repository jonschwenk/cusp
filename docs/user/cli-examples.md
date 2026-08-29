# Rebuild And Processing Commands

These examples show common CUSP commands. They are most useful if you want to
rebuild the dataset, make spatial summaries, or sample environmental
information on your own computer.

If you only want to use the released data, start with
[Download CUSP](../getting-started/release-products.md).

They assume you are running from the repository root with the `cusp`
environment activated:

```bash
conda activate cusp
```

Feature sampling uses your own Google Earth Engine login and project. Before
running feature examples, authenticate once and enter a project ID your
account can use. The variable remains available to later commands in the same
Bash session:

```bash
earthengine authenticate
read -r -p "Google Cloud / Earth Engine project ID: " CUSP_GEE_PROJECT
```

The feature examples pass that value explicitly through `--gee-project`.

The examples below use `exports/latest/cusp_v1.1.csv` as the input release
file. Replace that with the path to the CUSP release file you downloaded or
exported.

## Generate An Aggregated Derivative

From the repository root, the default aggregation is:

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
  behavior uses `31`. Because dates are linked consecutively, a chain of
  qualifying gaps can span more than 31 days; the calendar-year boundary is
  always preserved.
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
  --input exports/latest/cusp_v1.1.csv \
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
$InputPath = "exports\latest\cusp_v1.1.csv"
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
  --gee-project "$CUSP_GEE_PROJECT" \
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
  --gee-project "$CUSP_GEE_PROJECT" \
  --resume
```

PowerShell users can run the smoke feature example with:

```powershell
$GeeProject = Read-Host "Google Cloud / Earth Engine project ID"
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

## Feature Table For Observation Rows

Aggregated feature tables are useful for modeling and exploration, but they are
different from observation-keyed feature tables.

An observation-keyed table can be sampled from a versioned release:

```bash
python -m cusp.features \
  --input exports/latest/cusp_v1.1.csv \
  --output runs/examples/cusp_v1.1_features.csv \
  --manifest runs/examples/cusp_v1.1_features_manifest.json \
  --gee-project "$CUSP_GEE_PROJECT" \
  --resume
```

This derived output is keyed to `cusp_obs_id`, but it is not part of the
canonical CUSP release bundle.
