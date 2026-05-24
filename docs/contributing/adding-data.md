# Adding New Data To CUSP

CUSP maintainers will add datasets as they have time. Contributors are also
welcome to add datasets directly by preparing the data and opening a pull
request.

## Git Workflow

1. Fork or clone the CUSP repository.
2. Create a branch for your dataset.
3. Add the source files, processing script, and processed table under
   `data/<Source_Key>/`.
4. Rebuild and check CUSP locally.
5. Open a pull request and describe what was added.

```bash
git checkout -b add-example-2026
```

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

## Step 1: Create The Process Script

The processing script must be lowercase and start with `process_`:

```text
data/Example_2026/process_example_2026.py
```

## Step 2: Add The Metadata As A Docstring

Add the metadata as a docstring at the top of the process script. Use the
template and field definitions in
[Process script header guidelines](process-script-header-guidelines.md).

If a source needs manual preprocessing, external downloads, or a date
assumption, record that in the docstring.

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

Important expectations:

- `lat`, `lon` should be decimal degrees in `EPSG:4326`
- `date` should be `YYYY-MM-DD`
- `pf_observed` should be integer `0` or `1`
- `pf_depth`, `thaw_depth`, and `obs_limit` should be in centimeters
- `site_id` may be null if the source truly does not provide one

## Step 4: Resolve Source Interpretation

Your `process_<source>.py` script should handle source-specific interpretation
as clearly as possible, including:

- source-specific sentinel values
- unit conversion
- approximate or campaign-level dates
- method mapping to the CUSP vocabulary
- obvious within-source duplicates
- obvious invalid rows that only the source contributor can interpret correctly
- row-level quality flags for approximate dates, bounded observations,
  interpolated coordinates, summary statistics, source quality flags, or other
  caveats defined in `data/quality_flag_definitions.csv`

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

## Pull Request Checklist

- create `data/<Source_Key>/`
- add `process_<source_key_lower>.py`
- add TOML metadata docstring
- write `processed_<source_key_lower>.csv`
- keep source-specific interpretation inside the process script
- validate metadata
- run the source script
- rebuild the working observation table
- run QA

Maintainers make final release-clearance decisions. See
[Source release clearance](../maintainers/source-release-clearance-guidelines.md)
for the maintainer review model.
