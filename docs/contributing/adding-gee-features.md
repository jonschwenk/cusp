# Adding New GEE Features

You can add your own features for local/offline work, or suggest new Google
Earth Engine features through a pull request so they can be integrated into the
default CUSP feature set.

## Where The Sampler Lives

The main code is in:

- [cusp/features/io.py](https://github.com/jonschwenk/cusp/blob/main/cusp/features/io.py)
- [cusp/features/gee.py](https://github.com/jonschwenk/cusp/blob/main/cusp/features/gee.py)
- [cusp/features/registry.py](https://github.com/jonschwenk/cusp/blob/main/cusp/features/registry.py)
- [cusp/features/sampler.py](https://github.com/jonschwenk/cusp/blob/main/cusp/features/sampler.py)
- [cusp/features/__main__.py](https://github.com/jonschwenk/cusp/blob/main/cusp/features/__main__.py)

## What The Sampler Expects

The sampler can read:

- the main CUSP release table, such as `cusp_v1.1.csv`
- an aggregated CUSP table
- any point-like table with:
    - a canonical ID (`cusp_obs_id` or `cusp_30m_id`)
    - `lat`
    - `lon`
    - either `date` or `year`

## The Three Common Feature Types

### 1. Static Single-Band Image

Examples:

- `slope`
- `aspect`
- `soil_oc`
- `merit_hand`

These are the easiest to add.

### 2. Static Multi-Output Family

Examples:

- `soil_texture`
- `curvature`

These return multiple columns from one conceptual feature family.

### 3. Time-Aware Feature

Examples:

- `temperature`
- `precip`

These depend on `year` or `date` and may need explicit handling for collection
coverage gaps.

## Step 1: Add The Sampling Function

Add a sampling function in
[registry.py](https://github.com/jonschwenk/cusp/blob/main/cusp/features/registry.py).

The simplest pattern is a static, single-band image. This copyable example
uses a real MERIT Hydro asset under a deliberately separate feature name; use
the same structure with the asset, band, and output name appropriate for your
feature:

```python
def sample_example_hand(table, config, context):
    image = context.ee.Image("MERIT/Hydro/v1_0_1").select("hnd")
    return _sample_static_image(
        table=table,
        config=config,
        context=context,
        output_name="example_hand",
        image=image,
    )
```

If the feature needs custom logic, build it there but keep the output as a
DataFrame keyed by the canonical CUSP ID.

## Step 2: Register The Feature

Add a `FeatureDefinition` entry in
[registry.py](https://github.com/jonschwenk/cusp/blob/main/cusp/features/registry.py).

Each feature should define:

- `key`
- `output_columns`
- `description`
- `source_label`
- `temporal_mode`
- `sample_fn`
- optional `notes`

For the function above, add this immediately after the existing
`FEATURE_REGISTRY` dictionary in `registry.py`:

```python
FEATURE_REGISTRY["example_hand"] = FeatureDefinition(
    key="example_hand",
    output_columns=("example_hand",),
    description="Example height above nearest drainage feature.",
    source_label="MERIT/Hydro/v1_0_1",
    temporal_mode="static",
    sample_fn=sample_example_hand,
)
```

## Step 3: Decide Whether It Belongs In `base_v1`

If the feature should be sampled by default, add it to `BASE_FEATURE_SET`.

If not, leave it out. Confirm that the registry resolves it before starting a
live Earth Engine request:

```bash
python -c "from cusp.features.registry import resolve_feature_keys; print(resolve_feature_keys(['example_hand'], feature_set='none'))"
```

## Step 4: Document Coverage And Caveats

For any new feature, document:

- the Earth Engine collection name
- whether it is static or time-aware
- native or approximate resolution
- coverage limits
- whether partial overlap should be used
- when missing values should become `NaN`

If the feature has time limits, follow the same pattern used by the current
climate features: partial overlap is okay, no overlap should return `NaN`
instead of crashing.

## Step 5: Add Tests

At minimum:

- extend [tests/test_features.py](https://github.com/jonschwenk/cusp/blob/main/tests/test_features.py) if needed
- verify registry resolution works
- verify output columns merge correctly

If the feature requires new helper logic, add a focused unit test for that
logic too.

## Step 6: Run A Smoke Test

A good first smoke test is a tiny subset with one feature. First create the
input from the current release:

```python
from pathlib import Path

import pandas as pd

output = Path("runs/examples/cusp_v1.1_smoke25.csv")
output.parent.mkdir(parents=True, exist_ok=True)
pd.read_csv("exports/latest/cusp_v1.1.csv", nrows=25).to_csv(output, index=False)
```

Then authenticate, enter a usable project ID, and sample the newly registered
feature:

```bash
earthengine authenticate
read -r -p "Google Cloud / Earth Engine project ID: " CUSP_GEE_PROJECT
python -m cusp.features \
  --input runs/examples/cusp_v1.1_smoke25.csv \
  --output runs/examples/example_hand_smoke.csv \
  --manifest runs/examples/example_hand_smoke_manifest.json \
  --gee-project "$CUSP_GEE_PROJECT" \
  --feature-set none \
  --features example_hand \
  --chunk-size 25
```

Then inspect:

- row count
- null rate
- output column names
- whether the values look plausible

For full runs, prefer the default `5000` row chunks and use `--resume` when
continuing an interrupted run. The sampler checkpoints the output CSV and
manifest after each completed feature family.

## Step 7: Update Docs

Update:

- [Feature sampling](../user/feature-sampling.md)
- [README.md](https://github.com/jonschwenk/cusp/blob/main/README.md)

If the feature changes the default feature set, note that in
[CHANGELOG.md](https://github.com/jonschwenk/cusp/blob/main/CHANGELOG.md).

## Design Rules To Keep

- keep point sampling as the default
- use an optional buffer only when there is a real neighborhood-summary reason
- keep feature names stable and machine-friendly
- keep feature outputs joinable by the canonical ID
- prefer clear `NaN` behavior over brittle implicit assumptions

## Pull Request Checklist

- add sampling function
- register `FeatureDefinition`
- decide whether to add it to `BASE_FEATURE_SET`
- document collection, resolution, and temporal behavior
- add tests
- run a live smoke test
- update docs
