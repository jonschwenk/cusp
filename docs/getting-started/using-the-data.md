# Using the CUSP Data

CUSP releases are ordinary CSV files. You can use them in Python, R, a
spreadsheet, or GIS software without installing the CUSP package.

## Start With A Versioned Release

Download `cusp_vX.Y.csv` from the [Download CUSP](release-products.md) page.
Keep its `RELEASE_INFO.md` and version-matched `cusp_sources_vX.Y.bib` file with
your analysis so the data version and source citations remain recoverable.

Read [Caveats and limits](caveats.md) before selecting or excluding rows.

## Load The Table

This Python example loads the table and parses the observation date:

```python
import pandas as pd

cusp = pd.read_csv("cusp_v1.1.csv", parse_dates=["date"])

print(cusp.shape)
print(cusp.columns.tolist())
```

The [data schema](../user/data-schema.md) defines all columns and units.

## Interpret Rows Before Filtering

- Each row is one accepted CUSP observation, identified by `cusp_obs_id`.
- `pf_observed = 1` means the source reported permafrost at that place and
  time.
- `pf_observed = 0` means the source did not find permafrost within the depth
  or observation represented by that row; it does not establish absence at
  every depth or nearby location.
- Depth fields are in centimeters, and latitude and longitude use WGS84.
- `source` connects the row to its underlying dataset and citation.

The distinction between detection, bounded absence, and visual classification
is described in [Presence, absence, and observation limits](caveats.md#presence-absence-and-observation-limits).

## Work With Quality Flags

`quality_flags` is a semicolon-delimited set of caveat codes. Flags describe
measurement context and processing choices; they are not a general quality
score. Decide which flags matter for your scientific question before filtering.

For example, this identifies lower-bound absence rows without removing them:

```python
flag_sets = cusp["quality_flags"].fillna("").str.split(";")
has_lower_bound_absence = flag_sets.map(lambda flags: "LB" in flags)

lower_bound_absences = cusp.loc[has_lower_bound_absence]
```

See the complete [quality flag definitions](../user/quality-flags.md#flag-definitions).

## Preserve Provenance

Keep `cusp_obs_id` and `source` in derived tables. If you aggregate CUSP with
the repository tool, keep the membership sidecar and `aggregated_sources`
column as well. These fields make row-level checking and source attribution
possible later.

## Generate The Citations You Need

After creating your final subset, the CUSP citation helper can inspect its
`source` or `aggregated_sources` column and write a focused BibTeX file:

```bash
python -m cusp.citations \
  --input path/to/final_cusp_subset.csv \
  --master-bib exports/latest/cusp_sources_v1.1.bib \
  --output references.bib
```

Using the helper requires the [CUSP tools](../user/index.md). See
[Attribution and BibTeX](../user/data-use-and-attribution.md) for the full
citation responsibilities.

## Optional Next Steps

- [Aggregate observations](../user/aggregation-guide.md) when dense local
  sampling should not act like independent observations.
- [Sample environmental features](../user/feature-sampling.md) for a chosen
  observation or aggregation table.
- Review [source metadata](../user/source-metadata.md) when source-level
  processing and caveats matter to an analysis.
