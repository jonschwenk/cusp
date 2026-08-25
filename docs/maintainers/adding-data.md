# Adding New Data To CUSP

CUSP maintainers and invited collaborators use this workflow after a candidate
source has been reviewed through the
[data-intake process](../contributing/suggest-dataset.md). The CUSP team owns
the canonical processing decisions, quality flags, deduplication, validation,
and release integration.

## What To Add

For a new source called `Example_2026`, create:

```text
data/
  Example_2026/
    raw source files...
    process_example_2026.py
    processed_example_2026.csv
```

Use the source directory name as the canonical `source_key`.
Register that key by appending it to the `source` vocabulary in
`cusp/canonical_observation_schema.json`. This is an intentional registry
update, not a schema change.

## Step 1: Create The Process Script

The processing script must be lowercase and start with `process_`:

```text
data/Example_2026/process_example_2026.py
```

## Step 2: Add The Metadata As A Docstring

Add the metadata as a docstring at the top of the process script. Use the
template and field definitions in
[Process script header guidelines](process-script-header-guidelines.md).

If a source needs manual preprocessing, external downloads, a date assumption,
or source-specific deduplication, record that in the docstring. Duplication
notes should identify the compared source, the match fields and counts, which
source was retained, and whether any non-exact overlap remains.

## Step 3: Produce The Processed CSV

Your script should write:

```text
data/Example_2026/processed_example_2026.csv
```

The easiest path is to use the helpers in
[data_utils.py](https://github.com/jonschwenk/cusp/blob/main/cusp/data_utils.py)
where they fit, then finish with `data_utils.check_columns(df)` before
writing.

## Minimum Processed-Table Contract

The processed CSV must include these columns:

- `lon`
- `lat`
- `date`
- `source`
- `site_id`
- `pf_observed`
- `pf_depth`
- `thaw_depth`
- `obs_limit`

It should also include:

- `method`

The build currently fills a missing `method` column if necessary, but new
contributions should provide it directly whenever possible. If the observation
tool is truly unknown, set:

- `method = "unknown"`

Processors may also add observation-quality flags using boolean columns named
`quality_flag_<flag>`, where `<flag>` is listed in
`data/quality_flag_definitions.csv`. The build validates these names and writes
semicolon-delimited flag codes into the main-table `quality_flags` column.

The canonical 12-column table is frozen. Do not add source-specific columns to
it. Keep source-specific provenance in the processed and all-fields tables or
publish new release information as a sidecar. New source, method, or quality
flag codes may be appended to the machine-readable contract, but existing
codes and meanings must not be changed. A new quality flag must also be added
to `data/quality_flag_definitions.csv`.

Important expectations:

- `lat`, `lon` should be decimal degrees in `EPSG:4326`
- `date` should be `YYYY-MM-DD`
- `pf_observed` should be integer `0` or `1`
- `pf_depth`, `thaw_depth`, and `obs_limit` should be in centimeters
- `site_id` may be null if the source truly does not provide one
- a numeric detected thaw depth or permafrost depth should be represented as
  `pf_observed = 1`, regardless of the depth value
- `pf_observed = 0` should normally represent an explicit no-detection result
  and must have a positive `obs_limit`
- a visual presence/absence classification may leave `obs_limit` blank only
  when `quality_flag_visual_interpretation = True`; document why no
  point-specific observation limit exists
- absence rows should leave canonical `pf_depth` and `thaw_depth` blank; retain
  supporting source values in clearly named provenance columns

## Step 4: Resolve Source Interpretation

Your `process_<source>.py` script should handle source-specific interpretation
as clearly as possible, including:

- source-specific sentinel values
- unit conversion
- approximate or campaign-level dates
- method mapping to the CUSP vocabulary
- obvious within-source duplicates
- known cross-source overlap and the exact rule used to resolve it
- obvious invalid rows requiring source-specific interpretation or follow-up
  with source contacts
- row-level quality flags for approximate dates, bounded observations,
  interpolated coordinates, summary statistics, source quality flags, or other
  caveats defined in `data/quality_flag_definitions.csv`

Dense GPR picks should normally be aggregated with
`data_utils.aggregate_gpr_points()` at the CUSP default of 5 m. The grouping
columns must identify independent surveys, including observation date or thaw
year, so repeated measurements of the same footprint remain distinct. Any
different spacing must be justified in the process-script header.

Do not remove records solely because two surveys overlap in space. When a
synthesis contains identifiable copies of an original source, keep the
original-source rows and implement the filter inside the synthesis processor.
Record the compared sources, match fields, expected match counts, date handling,
and remaining uncertainty in both process-script headers.

## Step 5: Validate The Metadata

Check that the metadata docstring is parseable and complete:

```bash
python -m cusp.generate_process_script_metadata --check --strict data/Example_2026/process_example_2026.py
```

## Step 6: Run The Source Script

```bash
python data/Example_2026/process_example_2026.py
```

## Step 7: Rebuild And Validate CUSP

```bash
python -m cusp.build
python -m cusp.qc validate-observations
python -m cusp.aggregate
python -m cusp.qc validate-aggregated
```

If your source changes the official dataset contents, that should usually be
treated as a new dataset version under
[Versioning and exports](../release/versioning-and-exports.md).

## Ingestion Checklist

- create `data/<Source_Key>/`
- append the source key to the machine-readable contract
- add `process_<source_key_lower>.py`
- add TOML metadata docstring
- write `processed_<source_key_lower>.csv`
- keep source-specific interpretation inside the process script
- validate metadata
- run the source script
- rebuild the working observation table
- run QA

Maintainers make final release-clearance decisions. See
[Source release clearance](source-release-clearance-guidelines.md) for the
maintainer review model.
