# CUSP Process Script Metadata Guidelines

## Where Metadata Lives

Every source-processing script should start with a structured TOML docstring.
That docstring records the source citation, processing choices, known
limitations, and release-review fields close to the code that creates the CUSP
rows.

CSV summaries such as `PROCESS_SCRIPT_METADATA.csv` are generated from these
docstrings and should not be manually edited.

If a source emits row-level quality flags, document the reason in the relevant
`processing_assumptions`, `temporal_handling`, `spatial_handling`, or
`known_limitations` entry. The canonical flag vocabulary is
`data/quality_flag_definitions.csv`.

## Required Format

The module docstring must be valid TOML. The parser reads it without executing
the process script, then checks whether the expected fields are present.

## Field Definitions And Examples

<div class="cusp-wide-table" markdown="1">

| Field | Required? | Format / allowed values | What to enter | Example |
| --- | --- | --- | --- | --- |
| `metadata_schema_version` | yes | integer | Input the metadata schema version number. | `1` |
| `source_key` | yes | string | Use the exact source directory name. | `"Example_Source"` |
| `release_clearance` | yes | `approved`, `needs_review`, `deferred`, `do_not_release` | Contributors should usually use `needs_review`; maintainers update this after review. | `"needs_review"` |
| `permission_basis` | yes | `self_generated`, `published_literature`, `public_repository_terms`, `emailed_approval`, `verbal_approval`, `institutional_approval`, `other`, `needs_review` | Record why you think the source can be included. | `"public_repository_terms"` |
| `original_author` | no | string | Person who wrote or substantially updated the processing script. | `"Your Name"` |
| `last_substantive_update` | yes | `YYYY-MM-DD` string | Date of the last meaningful processing or metadata update. | `"2026-05-15"` |
| `source_dataset` | yes | multiline string | Citation, DOI, repository link, or short description of the original source. | `'''Dataset title, DOI, and access link.'''` |
| `processing_assumptions` | yes | TOML array of strings | Unit conversions, threshold choices, recoding decisions, and any other interpretation needed to create CUSP rows. Use `[]` if none. | `["Converted thaw depth from m to cm."]` |
| `temporal_handling` | no | TOML array of strings | How dates were preserved, inferred, rounded, or approximated. Use `[]` if none. | `["Only year was available; assigned YYYY-08-15."]` |
| `spatial_handling` | no | TOML array of strings | How coordinates were read, transformed, rounded, inferred, or filtered. Use `[]` if none. | `["Converted UTM coordinates to EPSG:4326."]` |
| `manual_steps` | yes | TOML array of strings | Any steps a person must do outside the script, such as downloading a restricted file. Use `[]` if none. | `["Download source CSV from repository landing page."]` |
| `known_limitations` | yes | TOML array of strings | Caveats a user or maintainer should know before relying on the processed rows. Use `[]` if none. | `["Exact observation day was not reported."]` |
| `external_dependencies` | yes | TOML array of strings | Data files, portals, credentials, or services needed to rerun the source workflow. Use `[]` if none. | `["Arctic Data Center DOI: ..."]` |
| `notes` | no | string | Any short note that does not fit elsewhere. Leave as `""` if unused. | `"Reviewed with source author."` |

</div>

## Recommended Template

```python
"""
metadata_schema_version = 1
source_key = "Example_Source"
release_clearance = "needs_review"
permission_basis = "published_literature"
original_author = "Your Name"
last_substantive_update = "2026-05-15"

source_dataset = '''
Canonical citation or dataset landing-page description.
'''

processing_assumptions = [
  "Key threshold or interpretation rule.",
  "Any important recoding rule.",
]

temporal_handling = [
  "How dates are derived, approximated, or preserved.",
]

spatial_handling = [
  "How coordinates are read, transformed, or inferred.",
]

manual_steps = []

known_limitations = [
  "Any approximation, unresolved edge case, or release caveat.",
]

external_dependencies = []

notes = ""
"""
```

## What Should Not Be Duplicated Here

Do not restate things that can be derived reliably elsewhere, such as:

- output CSV filename
- script path
- source directory name beyond `source_key`

Those should be derived by the metadata generator.

## Generated Metadata Summary

The structured headers are parsed by:

- [generate_process_script_metadata.py](https://github.com/jonschwenk/cusp/blob/main/cusp/generate_process_script_metadata.py)

That script writes:

- [PROCESS_SCRIPT_METADATA.csv](https://github.com/jonschwenk/cusp/blob/main/PROCESS_SCRIPT_METADATA.csv)

This CSV is generated and should not be manually edited.

## Validation

The metadata generator can:

- report scripts with structured TOML metadata
- report scripts with legacy free-form docstrings
- report parse or validation errors
- run in strict mode for contributor or CI checks
