# CUSP Reproducibility And Inclusion Exceptions

Date: 2026-04-08
Status: Initial exception register for Phase 3

## Purpose

This register tracks sources that are currently excluded, incomplete, or otherwise outside the clean reproducibility path for the canonical v1 observation-level release.

This is a working project document. Entries here should be revised as sources are clarified, rebuilt, or explicitly deferred.

## How To Read This Register

- `Current status`: how the source is treated in the repo today
- `Reason`: current rationale based on repo code, source scripts, and nearby documentation
- `Confidence`: how sure we are that the stated rationale is correct
- `Release implication`: what this means for the v1 release plan
- `Next action`: what needs to happen before the source can be considered resolved

## Current Exceptions

### `Chen_2015`

- Current status: removed from `data/` after duplicate review; retained as a bibliographic-only source for synthesis traceability
- Repo evidence:
  - the removed processing script stated: `THIS DATASET IS INCLUDED IN THE SCHAEFER DATA, DO NOT INCLUDE`
  - `data/cusp_sources.bib` and `data/cusp_sources_bibtex.csv` retain the `Chen_2015` reference with a note that it should not be ingested separately
  - `Jafarov_2016` and `Moore_et_al_2025` now carry DOI metadata for the included synthesis/related ABoVE sources
- Reason:
  - this appears to be an intentional de-duplication decision rather than a reproducibility failure
  - retaining the citation but removing the duplicate source directory avoids both duplicate observations and lost source provenance
- Confidence: high that it is intentionally duplicated; medium on the exact parent-source mapping
- Release implication:
  - this should remain out of the canonical observation release as a separate source
  - the reference should remain in the master bibliography for traceability when CUSP ingests a synthesis that may include its observations
- Next action:
  - no source-directory action remains
  - revisit only if CUSP adds a formal many-to-one source-provenance table for synthesis datasets

### `Beer_etal_2013`

- Current status: excluded from the canonical observation-level combine step; considered resolved as out of scope for the observation release
- Repo evidence:
  - `cusp/combine_data.py` explicitly skips `Beer_etal_2013`
  - the combine comment says it is interpolated map data with no dates
  - `data/Beer_etal_2013/process_beer_etal_2013.py` creates rows with `date = np.nan` and adds a comment that the data represent the period `1960-1987`
- Reason:
  - this is a gridded/interpolated map product rather than a dated observation dataset
  - it does not fit the current observation-level schema requirement for a valid date field
- Confidence: high
- Release implication:
  - should remain out of the canonical observation-level release
  - could potentially be treated later as a distinct auxiliary modeled/map product, but not as a standard CUSP observation source
- Next action:
  - keep excluded for v1 unless the project decides to support undated historical map products in a separate release track
  - keep on the deferred deletion list, but do not delete yet

### `Brown_etal_2000_calm`

- Current status: excluded from the canonical observation-level build after CALM supersession review
- Repo evidence:
  - `data/Brown_etal_2000_calm/process_brown_etal_2000_calm.py` processes a manually reformatted CALM summary workbook
  - the parser depends on fixed row ranges in `CALM_Summary_table.xlsx`
  - comparison against the newer `CALM` GTN-P/PANGAEA export shows this source is CALM-derived and has source-level date/value alignment problems
- Reason:
  - the newer `CALM` source is the canonical CALM/GTN-P annual ALT export
  - keeping both would retain duplicate CALM-derived observations, while the Brown workbook path is less reproducible and less faithful to the source metadata
- Confidence: high that this should not remain as a separate canonical observation source once `CALM` is included
- Release implication:
  - this source should stay excluded from the canonical observation-level release
  - retain the source directory for now until the final deletion pass, because the project may still want the historical paper citation for provenance
- Next action:
  - after `CALM` is promoted into the release build, delete or archive the Brown processed source and keep any needed citation/provenance note outside the canonical source list

### `Sadeghi_etal_2023`

- Current status: excluded from the canonical observation-level build pending source review
- Repo evidence:
  - `data/Sadeghi_etal_2023/process_sadeghi_etal_2023.py` describes the source as an InSAR-derived thaw-depth estimate product
  - the script assigns a representative date to a multi-year analysis window
  - the processed source currently emits only an unsupported source-specific method label
- Reason:
  - the canonical observation release is limited to direct observation workflows
  - surface-displacement-derived thaw-depth products may be useful related data, but they are outside the current method vocabulary
- Confidence: high that the current processed output is not a direct field-observation table; source-level review may still clarify whether any directly observed validation data are present elsewhere in the source package
- Release implication:
  - this source should remain out of the canonical observation release unless a direct-observation subset is identified and processed separately
- Next action:
  - inspect the source package and notebook to determine whether any direct permafrost observations exist apart from the derived product
  - if not, retain the source only as a related-data candidate outside the canonical observation table

### `Yi_etal_2020_ABoVE`

- Current status: excluded, deferred, and not currently reproducible from the checked-in repo alone
- Repo evidence:
  - `cusp/combine_data.py` explicitly skips `Yi_etal_2020_ABoVE`
  - the combine comment says the source is too large to load directly and needs to be processed online
  - `data/Yi_etal_2020_ABoVE/process_yi_etal_2020_above.py` now uses repo-relative paths and the canonical source key
  - the raw file `Alaska_active_layer_thickness_1km_2001-2015.nc4` is now available locally, but it is gitignored and treated as an external input
  - the current netCDF would flatten to about `43,956,000` time-grid rows if exported directly
- Reason:
  - the source still depends on an external/local raw input outside normal Git tracking
  - the current flatten-to-CSV workflow is likely too large and needs redesign before this source is release-ready
- Confidence: high
- Release implication:
  - this source is a true reproducibility exception for v1
  - it should stay on the cleanup-later list unless we either:
    - provide a documented external-download workflow, or
    - host the required source data elsewhere and document access
- Next action:
  - leave this on the investigate/cleanup-later list for now
  - if later brought in scope, replace hardcoded paths with repo-relative logic and document the external-data acquisition step

### `Wilcox_2015`

- Current status: excluded and incomplete for the current observation-level pipeline; needs later investigation
- Repo evidence:
  - `cusp/combine_data.py` explicitly skips `Wilcox_2015`
  - the combine comment says there are no lat/lon data for observations
  - source files are present under `data/Wilcox_2015/`, but there is no checked-in `processed_wilcox_2015.csv`
- Reason:
  - the current observation-level release requires geolocated records, and this source apparently does not meet that requirement in its current form
- Confidence: medium
  - the combine comment is clear, but the repo still needs a fuller note describing whether coordinates are fundamentally absent or just not yet recoverable
- Release implication:
  - this should remain excluded for v1 unless geolocation can be reconstructed in a scientifically defensible way
- Next action:
  - keep on the investigate-later list
  - add a short source note describing whether this is permanently non-geolocatable or just not yet processed

## Running Lists

### Revisit For Possible Inclusion

- `Sadeghi_etal_2023`

### Investigate Or Clean Up Later

- `Yi_etal_2020_ABoVE`
- `Wilcox_2015`

### Deferred Deletion Candidates

These are not to be deleted now. Keep them skipped during ongoing development and revisit deletion near the end of release cleanup after documentation decisions are settled.

- `Beer_etal_2013`
- `Brown_etal_2000_calm`

## Additional Non-Blocking Cleanup Items

These are not currently exclusion reasons, but they should be cleaned up before deeper automation:

  - `Yi_etal_2020_ABoVE`: flattening the full netCDF directly to CSV is still too large for the canonical observation-level workflow

## Recommended Immediate Decisions

1. Keep `Chen_2015` as a bibliographic-only duplicate/absorbed source unless CUSP adds formal sub-source provenance for synthesis datasets.
2. Treat `Yi_etal_2020_ABoVE` as a formal reproducibility exception unless and until the external-data workflow and the oversized flattening workflow are redesigned and documented.
3. Leave `Beer_etal_2013`, `Brown_etal_2000_calm`, `Sadeghi_etal_2023`, and `Wilcox_2015` excluded for v1 unless the release scope changes.
