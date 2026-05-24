# Source Metadata

CUSP keeps source-level metadata separate from the observation table. These
tables help users understand which source datasets are represented in CUSP and
which source-wide caveats apply before row-level filtering.

## Source Quality Metadata

The generated `data/source_quality_metadata.csv` table has one row per CUSP
source directory. It summarizes quality flags that apply broadly to a source.
It is not an observation table, and it does not replace row-specific flags in
`cusp_vX.Y.csv`.

The source-level quality table uses the same compact codes defined in
[Quality flags](quality-flags.md).

| Column | Meaning |
|---|---|
| `source` | CUSP source key |
| `source_quality_flags` | Semicolon-delimited quality flag codes applied source-wide |
| `source_quality_flag_names` | Semicolon-delimited full flag names |
| `source_quality_flag_categories` | Semicolon-delimited flag categories represented for the source |

Blank source-level flag fields mean no current source-wide quality flag is
assigned. Individual observations from that source may still receive row-level
flags during the build.

## Source Reference Crosswalk

The generated `data/source_reference_crosswalk.csv` table links included source
keys to citation metadata from `data/cusp_sources_bibtex.csv`.

| Column | Meaning |
|---|---|
| `source` | CUSP source key used in observation tables |
| citation fields | BibTeX-derived source citation metadata, when available |

Use the crosswalk to inspect source citation coverage. Use
`cusp_sources_vX.Y.bib` from a release bundle when citing the sources included
in a versioned CUSP release.
