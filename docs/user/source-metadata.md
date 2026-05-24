# Source Metadata

CUSP keeps source-level metadata separate from the observation table. These
tables help users understand which source datasets are represented in CUSP and
which source-wide caveats apply before row-level filtering.

## Dataset Table

The generated `data/source_metadata.csv` table is the main source-level
dataset table. It combines observation counts, source-wide quality flags,
duplication caveats, and selected citation metadata into one row per included
CUSP source.

| Column | Meaning |
|---|---|
| `source` | CUSP source key |
| `N_pf_Y` | Number of rows where permafrost is observed |
| `N_pf_N` | Number of rows where permafrost is not observed |
| `N_pf` | Total number of permafrost presence/absence rows |
| `bb_area_km2` | Approximate source bounding-box area in square kilometers |
| `N_alt` | Number of rows with a positive permafrost-depth value |
| `source_quality_flags` | Semicolon-delimited source-wide quality flag codes |
| `source_quality_flag_names` | Semicolon-delimited full source-wide quality flag names |
| `source_quality_flag_categories` | Semicolon-delimited source-wide quality flag categories |
| `has_duplication_caveat` | `true` when the source has a known possible duplicate or overlap caveat |
| citation fields | Selected BibTeX-derived citation metadata, when available |

The duplication field is a summary helper. Details about overlap decisions
remain in source processing headers, GitHub dataset issues, and row-level
quality flags where applicable.

## Source Quality Metadata

The generated `data/source_quality_metadata.csv` table has one row per CUSP
source directory. It is the quality-specific input used to build
`source_metadata.csv`. It summarizes quality flags that apply broadly to a
source. It is not an observation table, and it does not replace row-specific
flags in `cusp_vX.Y.csv`.

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
