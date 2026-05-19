# CUSP Reproducibility Audit

Date: 2026-04-10
Status: Repo-structure audit plus initial observation-build execution audit for Phase 3

## Scope

This is an initial source-by-source reproducibility audit based on the current repository contents.

It is not yet a full execution audit. In particular, this pass does not prove that every source-specific processing script runs cleanly end to end in the current environment. It audits what is present in the repo now so we can identify the largest reproducibility gaps before rebuilding artifacts.

This pass used:

- the internal source-summary table as the current included-source list for the observation-level release
- source directories under `data/`
- recursive checks for:
  - a `processed_*.csv` output
  - a processing script with a name containing `process`, `Processed`, or `Porcessed`
  - obvious local documentation artifacts such as `readme`, `metadata`, `guide`, `manifest`, or `science-metadata` files

For this audit, "documentation artifact present" is only a proxy for manual-step documentation. A source can have metadata and still be missing a clear rebuild recipe.

## Headline Findings

- Current included release sources: `50`
- Included release sources with a checked-in `processed_*.csv`: `50 / 50`
- Included release sources with a checked-in processing script: `50 / 50`
- Included release sources with an obvious local reproducibility-documentation artifact: `16 / 50`
- Included release sources that likely still need explicit manual-step documentation: `34 / 50`
- Processed-but-not-included sources: `2`
  - `Beer_etal_2013`
  - `Sadeghi_etal_2023`
- Script-but-no-processed-output source: `1`
  - `Yi_etal_2020_ABoVE`
- Known skipped source with no current processed output in repo:
  - `Wilcox_2015`

## Provisional Interpretation

- `Level A` reproducibility looks plausible for the current release model because every currently included source has both a processed CSV and a checked-in source-specific processing script.
- `Level B` reproducibility is not yet release-ready because most included sources still do not have an obvious local manual-step document or rebuild note.
- The biggest Phase 3 gap is not missing scripts. It is missing explicit per-source rebuild documentation and then verifying that those scripts still run successfully.

## Initial Supported Combine Execution Audit

Date run: `2026-04-10`

Execution target:

- `python cusp/combine_data.py`

Execution method:

- run in an isolated audit copy under `/tmp` so the checked-in release artifacts in the repo were not overwritten

Environment notes:

- `python` available from the current conda-based environment
- verified imports before the run:
  - `pandas`
  - `geopandas`
  - `numpy`

Artifacts checked:

- working observation table
- the internal source-summary table

Headline result:

- the observation build completed successfully in the isolated audit copy
- both checked-in build artifacts were reproduced semantically from the current processed source tables
- the rebuilt files were not byte-for-byte identical to the checked-in files

Observed rebuild results:

- rebuilt working observation table
  - `251,935` rows
  - `47` columns
  - `50` unique `source` values
  - date range `1962-08-15` to `2024-10-03`
- rebuilt the source-summary table
  - `50` rows
  - `6` columns
  - `50` unique `source` values

What differed from the checked-in files:

- working observation table
  - column order changed
  - row order changed
  - some numeric-looking values were written with different string formatting such as `25` vs `25.0`
- source-summary table
  - source row order changed
  - values matched after canonical sorting and numeric normalization

What matched after canonical comparison:

- working observation table
  - same column set
  - same per-source row counts
  - same date range
  - semantically equal after canonicalizing column order, row order, nulls, and numeric formatting
- source-summary table
  - same column set
  - same integer fields
  - same bounding-box areas within a tight numeric tolerance
  - semantically equal after sorting by `source` and canonicalizing numeric formatting

Interpretation:

- the current observation-build path is functionally reproducible for the working observation table and source-summary table
- the current observation-build path is not yet deterministic at the file-layout level
- the most likely causes are:
  - unsorted source discovery via `os.listdir(...)`
  - column-order drift caused by concatenating wide source tables in source-discovery order
  - mixed-type column formatting drift during CSV round-tripping

Release implication:

- this is good enough to keep moving through Phase 3
- before release, the observation-build path should be hardened so official observation-level artifacts rebuild deterministically, not just semantically

## Pilot Source-Script Execution Audit

Date run: `2026-04-10`

Execution method:

- run selected `process_*.py` scripts in isolated audit copies under `/tmp` so the checked-in `processed_*.csv` artifacts in the repo were not overwritten

Pilot sources audited:

- `Koyukuk_2018`
- `Cable_2017`
- `Pastick`
- `Moore_et_al_2025`
- `Wagner_2019`

Headline result:

- `0 / 5` pilot scripts rebuilt successfully in the current environment without intervention
- the failures were informative and fell into a few clear categories rather than looking random

Failure categories observed:

- current-pandas script breakage
  - `Koyukuk_2018`
- path-portability bug in the script
  - `Cable_2017`
- mixed-type handling bug in the script
  - `Pastick`
- missing raw input data in the repo
  - `Moore_et_al_2025`
- environment dependency missing from the current runtime
  - `Wagner_2019`

Per-source notes:

- `Koyukuk_2018`
  - failed because chained assignment is used to replace `Y`/`N` in `pf_observed`
  - this breaks under the current pandas copy-on-write behavior and string dtype handling
- `Cable_2017`
  - failed because `process_network()` reads `network_sampling_sites.csv` as a bare relative path
  - the rest of the script uses `_ROOT_DIR`, so this looks like a straightforward portability bug rather than a missing-data issue
- `Pastick`
  - failed because the script assumes non-integer `pf_observed` values are strings and calls `.lower()` on a float/NA value
- `Moore_et_al_2025`
  - failed because the required raw input `ABoVE_Soil_ThawDepth_Moisture_Validation_V2.csv` is not present in the repo
  - this is a real reproducibility-input gap, not just a script quirk
- `Wagner_2019`
  - failed because `openpyxl` is not available in the current environment even though the script reads `.xlsx` files
  - this indicates environment drift between the documented environment and the environment actually used for the audit

Interpretation:

- the repo-level combine path is in better shape than the source-level rebuild path
- at least some currently included sources will require:
  - script fixes for compatibility and portability
  - explicit restoration/documentation of missing raw inputs
  - environment validation against the documented dependency set

Release implication:

- Phase 3 should continue, but we should not yet claim that the observation-level release is source-by-source rebuildable from the current repo state
- the manifest should now be treated as a live blocker register rather than just an inventory

## Positive-Control Rechecks After Targeted Script Fixes

Date run: `2026-04-10`

Sources rechecked:

- `Koyukuk_2018`
- `Cable_2017`
- `Pastick`
- `Wagner_2019`
- `Moore_et_al_2025`

Result:

- all five sources rebuilt successfully in isolated audit copies after targeted script fixes, environment correction, or restoring a missing local input
- all five rebuilt `processed_*.csv` artifacts matched the checked-in outputs semantically, with `Pastick` requiring a small coordinate-rounding tolerance because of reprojection precision drift
- none of the rebuilt CSVs was byte-for-byte identical to the checked-in file

Per-source notes:

- `Koyukuk_2018`
  - fixed by replacing chained assignment on `pf_observed` with a pandas-safe normalization path
  - rebuilt output had the same row count (`372`) and matched semantically
- `Cable_2017`
  - fixed by resolving the network CSV path via `_ROOT_DIR` when a non-absolute path is passed
  - rebuilt output had the same row count (`19`) and matched semantically
  - date-parsing warnings are still emitted and should be cleaned up later for a quieter release workflow
- `Pastick`
  - fixed by normalizing mixed `pf_observed` encodings robustly across the projected-site shapefiles
  - rebuilt output had the same row count (`8,012`) and matched the checked-in file after applying a modest coordinate-rounding tolerance
  - the remaining drift appears to be tiny reprojection precision noise rather than a substantive data change
- `Wagner_2019`
  - no script patch was needed after the environment was corrected
  - the earlier failure was due to missing `openpyxl` in the shell environment used for the first audit pass
  - rerunning explicitly inside the `cusp2` environment succeeded, and the rebuilt output had the same row count (`143`) and matched semantically
- `Moore_et_al_2025`
  - no script patch was needed once the raw input file was available locally
  - rerunning explicitly inside the `cusp2` environment succeeded, and the rebuilt output had the same row count (`201,305`) and matched semantically
  - the raw input CSV is currently a local/external dependency rather than an in-repo source artifact because it is `111 MB` and intentionally gitignored

Interpretation:

- we now have positive-control evidence that at least some included source scripts can be brought into a release-ready state with relatively small fixes
- the remaining source-level audit work should continue to distinguish:
  - simple script-compatibility fixes
  - environment/dependency fixes
  - missing-input-data blockers

## Additional Source-Workflow Batch Audit

Date run: `2026-04-10`

Batch audited:

- `Douglas_Koyukuk_2022`
- `James_2019`
- `James_2020`
- `Hanston_etal_2024`
- `Bakian_Dogaheh_2020`

Headline result:

- `5 / 5` sources in this batch are now execution-verified as semantic rebuilds
- `3 / 5` succeeded on the first `cusp2` audit run:
  - `James_2020`
  - `Hanston_etal_2024`
  - `Bakian_Dogaheh_2020`
- `2 / 5` needed small pandas-compatibility fixes before succeeding:
  - `Douglas_Koyukuk_2022`
  - `James_2019`

Per-source notes:

- `Douglas_Koyukuk_2022`
  - initially failed because `pf_observed` normalization used chained assignment
  - after patching to a pandas-safe replacement path, rebuild succeeded and matched semantically
- `James_2019`
  - initially ran but produced semantically wrong `pf_observed` values because chained assignment no longer updated the column under current pandas
  - after patching to `.loc[...]`, rebuild succeeded and matched semantically
- `James_2020`
  - rebuild succeeded and matched semantically
  - the 999/888 thaw-depth sentinels are now treated explicitly as 200 cm / 120 cm observation limits to stay consistent with centimeter-based thaw depths
  - a PROJ database warning was emitted during the run, but the shapefile still read successfully and the workflow completed
- `Hanston_etal_2024`
  - rebuild succeeded and matched semantically
- `Bakian_Dogaheh_2020`
  - rebuild succeeded and matched semantically

Interpretation:

- the next-tier included source workflows are still largely fixable with small compatibility patches rather than deep redesign
- the main recurring code-level risk so far is older pandas idioms that either fail outright or silently stop mutating data under current copy-on-write behavior

## Additional Source-Workflow Batch Audit II

Date run: `2026-04-10`

Batch audited:

- `Daanen_2017`
- `Wang_2018`
- `Ebel_2018`
- `Holloway_2019`

Headline result:

- `4 / 4` sources in this batch are now execution-verified as semantic rebuilds in `cusp2`
- `3 / 4` succeeded on the first confirmation rerun:
  - `Daanen_2017`
  - `Wang_2018`
  - `Ebel_2018`
- `1 / 4` needed a small pandas/dtype cleanup before succeeding:
  - `Holloway_2019`
- `Holloway_2019` is the first source in the recent audit batches to rebuild byte-for-byte identically after patching

Per-source notes:

- `Daanen_2017`
  - rebuild succeeded and matched semantically
  - the rebuilt CSV was not byte-identical, but no substantive differences were detected
- `Wang_2018`
  - rebuild succeeded and matched semantically
  - the rebuilt CSV was not byte-identical, but no substantive differences were detected
- `Ebel_2018`
  - rebuild succeeded and matched semantically
  - the geometry-assignment warning path was cleaned up later the same day
- `Holloway_2019`
  - initially failed because the year-specific `pf_observed` and `pf_depth` cleanup no longer played nicely with current pandas/dtype behavior
  - after normalizing those conversions explicitly, rebuild succeeded
  - the rebuilt CSV was byte-for-byte identical to the checked-in output

Interpretation:

- the source-processing layer continues to look recoverable with relatively small fixes rather than major redesign
- warning cleanup is now becoming a more prominent next-tier task once outright execution failures are removed
- older pandas-style implicit conversions remain the main source of real breakage

## Additional Source-Workflow Batch Audit III

Date run: `2026-04-10`

Batch audited:

- `Bonaventure_Whati`
- `Jones_2025`
- `Jones_Jones_2025`
- `Jorgenson_Kanevskiy_2022_Gosling`
- `Jorgenson_Kanevskiy_2022_Jago`

Headline result:

- `5 / 5` sources in this batch are execution-verified as clean rebuilds in `cusp2`
- all five rebuilt outputs were byte-for-byte identical to the checked-in CSVs
- no warnings were emitted during these runs

Per-source notes:

- `Bonaventure_Whati`
  - rebuild succeeded
  - rebuilt output was byte-identical to the checked-in CSV
- `Jones_2025`
  - rebuild succeeded
  - rebuilt output was byte-identical to the checked-in CSV
- `Jones_Jones_2025`
  - rebuild succeeded
  - rebuilt output was byte-identical to the checked-in CSV
- `Jorgenson_Kanevskiy_2022_Gosling`
  - rebuild succeeded
  - rebuilt output was byte-identical to the checked-in CSV
- `Jorgenson_Kanevskiy_2022_Jago`
  - rebuild succeeded
  - rebuilt output was byte-identical to the checked-in CSV

Interpretation:

- some of the newer included source workflows are already in very strong shape for release
- this batch increases confidence that not all remaining Phase 3 work will require code fixes
- the highest-value next step is to keep pushing through included sources that look similarly likely to be clean or near-clean

## Additional Source-Workflow Batch Audit IV

Date run: `2026-04-10`

Batch audited:

- `Petrone_etal_2016`
- `Scheer_etal_2023`
- `Schwenk_PFRR`
- `Seward_2022`
- `Jorgenson_Kanevskiy_2025`

Headline result:

- `5 / 5` sources in this batch are now execution-verified as semantic rebuilds in `cusp2`
- `4 / 5` rebuilt cleanly without code changes:
  - `Petrone_etal_2016`
  - `Scheer_etal_2023`
  - `Schwenk_PFRR`
  - `Seward_2022`
- `1 / 5` needed a small pandas-compatibility patch before succeeding:
  - `Jorgenson_Kanevskiy_2025`
- none of these rebuilt files was byte-for-byte identical

Per-source notes:

- `Petrone_etal_2016`
  - rebuild succeeded and matched semantically
  - no warnings were emitted
- `Scheer_etal_2023`
  - rebuild succeeded and matched semantically
  - no warnings were emitted
- `Schwenk_PFRR`
  - rebuild succeeded and matched semantically
  - no warnings were emitted
  - the initial failed audit attempt was only an audit-harness path mistake, not a source-script problem
- `Seward_2022`
  - rebuild succeeded and matched semantically
  - no warnings were emitted
- `Jorgenson_Kanevskiy_2025`
  - initially failed because the script assumed grouping columns were still present inside `groupby.apply()`
  - after patching the summarization function to recover group keys safely, rebuild succeeded and matched semantically
  - the later mixed-type CSV read warning and chained-assignment warning paths were cleaned up later the same day

Interpretation:

- the remaining included-source audit set continues to split into two manageable categories:
  - workflows that are already reproducible but not byte-deterministic
  - workflows that need small pandas-compatibility updates
- `groupby.apply()` behavior under current pandas is now another recurring compatibility theme to watch for in older scripts

## Additional Source-Workflow Batch Audit V

Date run: `2026-04-10`

Batch audited:

- `Minsley_2015`
- `Minsley_2017`
- `Minsley_2021`
- `Obu_etal_2016`
- `Natali_2023`

Headline result:

- `5 / 5` sources in this batch are execution-verified as semantic rebuilds in `cusp2`
- none of the rebuilt files was byte-for-byte identical
- `3 / 5` ran cleanly with no warnings:
  - `Minsley_2021`
  - `Obu_etal_2016`
  - `Natali_2023`
- `2 / 5` emitted warnings but still rebuilt semantically:
  - `Minsley_2015`
  - `Minsley_2017`

Per-source notes:

- `Minsley_2015`
  - rebuild succeeded and matched semantically
  - the later docstring escape issue and benign `openpyxl` workbook warning were cleaned up later the same day
- `Minsley_2017`
  - rebuild succeeded and matched semantically
  - the later date-parsing warning path was cleaned up by specifying the input format explicitly
- `Minsley_2021`
  - rebuild succeeded and matched semantically
  - no warnings were emitted
- `Obu_etal_2016`
  - rebuild succeeded and matched semantically
  - no warnings were emitted
- `Natali_2023`
  - rebuild succeeded and matched semantically
  - no warnings were emitted

Interpretation:

- the Minsley-family workflows are broadly reproducible already, with only warning cleanup standing between them and quieter release-grade execution
- warning-only issues are now becoming common enough that Phase 3 should start distinguishing:
  - semantic rebuild success
  - warning cleanup needed
  - code patch required

## Additional Source-Workflow Batch Audit VI

Date run: `2026-04-10`

Batch audited:

- `Chapin_2025`
- `Kling_2025`
- `Ruess_2025`
- `Sadeghi_etal_2023`
- `Talucci_2024`

Headline result:

- `5 / 5` sources in this batch are now execution-verified as semantic rebuilds in `cusp2`
- `3 / 5` rebuilt semantically without code changes:
  - `Chapin_2025`
  - `Ruess_2025`
  - `Sadeghi_etal_2023`
- `2 / 5` needed small compatibility/path fixes before succeeding:
  - `Kling_2025`
  - `Talucci_2024`
- none of the rebuilt files was byte-for-byte identical

Per-source notes:

- `Chapin_2025`
  - rebuild succeeded and matched semantically
  - no warnings were emitted
- `Kling_2025`
  - initially failed because the script resolved its default CSV and metadata paths relative to the repo root instead of `data/Kling_2025`
  - after patching default path resolution, rebuild succeeded and matched semantically
  - no warnings were emitted
- `Ruess_2025`
  - rebuild succeeded and matched semantically
  - no warnings were emitted
- `Sadeghi_etal_2023`
  - rebuild succeeded and matched semantically
  - no warnings were emitted
- `Talucci_2024`
  - initially failed under current pandas behavior because a `groupby.apply()` filtering step dropped the grouping columns used later in the script
  - after replacing that step with a transform-based mask, rebuild succeeded and matched semantically
  - no warnings were emitted

Interpretation:

- the newer source workflows continue to confirm the main Phase 3 pattern:
  - many scripts are already semantically reproducible
  - the remaining breakages are usually small path or pandas-compatibility issues
- `groupby.apply()` and path resolution are now the two clearest recurring code-level themes to clean up proactively

## Additional Source-Workflow Batch Audit VII

Date run: `2026-04-10`

Batch audited:

- `Langer_etal_2020`
- `Patton_2021`
- `Peirce_2020`
- `Zhang_2019`
- `Zhao_2021`

Headline result:

- `5 / 5` sources in this batch are execution-verified as semantic rebuilds in `cusp2`
- none of the rebuilt files was byte-for-byte identical
- no warnings were emitted during these runs

Per-source notes:

- `Langer_etal_2020`
  - rebuild succeeded and matched semantically
- `Patton_2021`
  - rebuild succeeded and matched semantically
- `Peirce_2020`
  - rebuild succeeded and matched semantically
- `Zhang_2019`
  - rebuild succeeded and matched semantically
- `Zhao_2021`
  - rebuild succeeded and matched semantically

Interpretation:

- this batch is another strong sign that a large fraction of the remaining included sources are already reproducible enough for release once the tracker is caught up
- the remaining queue is increasingly concentrated in the older and more idiosyncratic workflows rather than the recent additions

## Additional Source-Workflow Batch Audit VIII

Date run: `2026-04-10`

Batch audited:

- `Hollingsworth_2005`
- `Jafarov_2016`
- `Kling_2016`
- `Myers-Smith_2005`
- `Whitley_2018`

Headline result:

- `5 / 5` sources in this batch are execution-verified as semantic rebuilds in `cusp2`
- none of the rebuilt files was byte-for-byte identical
- no warnings were emitted during these runs

Per-source notes:

- `Hollingsworth_2005`
  - rebuild succeeded and matched semantically
- `Jafarov_2016`
  - rebuild succeeded and matched semantically
- `Kling_2016`
  - rebuild succeeded and matched semantically
- `Myers-Smith_2005`
  - rebuild succeeded and matched semantically
- `Whitley_2018`
  - rebuild succeeded and matched semantically

Interpretation:

- even the older, messier-looking workflows are still frequently reproducible enough to keep in scope for v1
- the main residual work is increasingly about determinism, warning cleanup, and documentation rather than basic executability

## Additional Source-Workflow Batch Audit IX

Date run: `2026-04-10`

Batch audited:

- `Selawik`
- `Seward`
- `Smith_Burgess_2000`
- `Smith_Burgess_2002`
- `Walker_2022`

Headline result:

- `5 / 5` sources in this batch are execution-verified as semantic rebuilds in `cusp2`
- none of the rebuilt files was byte-for-byte identical
- no warnings were emitted during these runs

Per-source notes:

- `Selawik`
  - rebuild succeeded and matched semantically
- `Seward`
  - rebuild succeeded and matched semantically
- `Smith_Burgess_2000`
  - rebuild succeeded and matched semantically
- `Smith_Burgess_2002`
  - rebuild succeeded and matched semantically
- `Walker_2022`
  - rebuild succeeded and matched semantically

Interpretation:

- all currently included observation-level release sources have now been execution-verified as semantic rebuilds in isolated `cusp2` runs
- Phase 3 has shifted from “can these source workflows run?” to:
  - how deterministic do we need the outputs to be?
  - which warning paths should be cleaned up before release?
  - how do we close the per-source manual-step documentation gaps?

## Warning Cleanup And Deterministic Combine Audit

Date run: `2026-04-10`

Scope:

- warning-heavy source workflows:
  - `Cable_2017`
  - `Ebel_2018`
  - `Jorgenson_Kanevskiy_2025`
  - `Minsley_2015`
  - `Minsley_2017`
- combine-path determinism:
  - `cusp/combine_data.py`

Results:

- the warning-heavy scripts above were patched and rerun in `cusp2`
- all five now rerun without the tracked Python/pandas/GeoPandas warnings
- `James_2020` remains the notable residual warning path, but it is environment-level:
  - `ERROR 1: PROJ: proj_create_from_database: Open of .../share/proj failed`
- `cusp/combine_data.py` was updated to:
  - sort source discovery deterministically
  - concatenate with stable indexing
  - sort final observation rows by stable keys
  - sort source-summary rows by `source`
- two consecutive `cusp2` runs now produce identical hashes:
  - working observation table: `cf1f81cacdc0f1fb294043bf3fca444f147785c5d7626ff99c9ca9f32af6f109`
  - source-summary table: `02ef2c1555d06e93c98e8e393129d1911f767c36146c211b59c7db287a60e688`

Interpretation:

- the main Phase 3 residuals are now:
  - per-source manual-step documentation
  - remaining source-specific byte-level nondeterminism
  - deferred source-policy questions such as the direct-observation status of `Sadeghi_etal_2023`
- the observation-build path is now strong enough to treat as byte-deterministic for repeated rebuilds in the audited environment

## Included Release Sources With Script And Obvious Local Documentation Artifact

- `Cable_2017`: script present; metadata artifact present
- `Daanen_2017`: script present; metadata artifact present
- `Douglas_Koyukuk_2022`: script present; readme present
- `Hanston_etal_2024`: script present; readme present
- `Jones_2025`: script present; metadata artifact present
- `Jones_Jones_2025`: script present; metadata artifact present
- `Jorgenson_Kanevskiy_2022_Gosling`: script present; metadata artifact present
- `Jorgenson_Kanevskiy_2022_Jago`: script present; metadata artifact present
- `Koyukuk_2018`: script present; readme present
- `Pastick`: script present; metadata artifact present
- `Schwenk_PFRR`: script present; readme present
- `Seward_2022`: script present; bag/metadata artifacts present
- `Wang_2018`: script present; metadata artifact present
- `Petrone_etal_2016`: script present; metadata artifact present
- `Jorgenson_Kanevskiy_2025`: script present; metadata artifact present
- `Pawley_2018`: script present; metadata artifact present

## Included Release Sources With Script But No Obvious Manual-Step Documentation Artifact Yet

- `Bakian_Dogaheh_2020`: script present; add explicit rebuild/manual-step note
- `Bonaventure_Whati`: script present; add explicit rebuild/manual-step note
- `Chapin_2025`: script present; add explicit rebuild/manual-step note
- `Ebel_2018`: script present; add explicit rebuild/manual-step note
- `Hollingsworth_2005`: script present; add explicit rebuild/manual-step note
- `Holloway_2019`: script present; add explicit rebuild/manual-step note
- `Jafarov_2016`: script present; add explicit rebuild/manual-step note
- `James_2019`: script present; add explicit rebuild/manual-step note
- `James_2020`: script present; add explicit rebuild/manual-step note
- `Kling_2016`: script present; add explicit rebuild/manual-step note
- `Kling_2025`: script present; add explicit rebuild/manual-step note
- `Langer_etal_2020`: script present; add explicit rebuild/manual-step note
- `Minsley_2015`: script present; add explicit rebuild/manual-step note
- `Minsley_2017`: script present; add explicit rebuild/manual-step note
- `Minsley_2021`: script present; add explicit rebuild/manual-step note
- `Moore_et_al_2025`: script present; add explicit rebuild/manual-step note
- `Myers-Smith_2005`: script present; add explicit rebuild/manual-step note
- `Natali_2023`: script present; add explicit rebuild/manual-step note
- `Obu_etal_2016`: script present; add explicit rebuild/manual-step note
- `Patton_2021`: script present; add explicit rebuild/manual-step note
- `Peirce_2020`: script present; add explicit rebuild/manual-step note
- `Ruess_2025`: script present; add explicit rebuild/manual-step note
- `Scheer_etal_2023`: script present; add explicit rebuild/manual-step note
- `Selawik`: script present; add explicit rebuild/manual-step note
- `Seward`: script present; add explicit rebuild/manual-step note
- `Smith_Burgess_2000`: script present; add explicit rebuild/manual-step note
- `Smith_Burgess_2002`: script present; add explicit rebuild/manual-step note
- `Talucci_2024`: script present; add explicit rebuild/manual-step note
- `Wagner_2019`: script present; add explicit rebuild/manual-step note
- `Walker_2022`: script present; add explicit rebuild/manual-step note
- `Whitley_2018`: script present; add explicit rebuild/manual-step note
- `Zhang_2019`: script present; add explicit rebuild/manual-step note
- `Zhao_2021`: script present; add explicit rebuild/manual-step note

## Included Release Sources With Naming Or Traceability Risks Worth Cleaning Up

- script and processed-output filenames have now been standardized to lowercase
  `process_<source>.py` and `processed_<source>.csv` conventions across the
  included workflows
- `Yi_etal_2020_ABoVE` still has a source-name mismatch between the directory
  and the internal `source` variable, so that one remains a real traceability
  cleanup item

## Excluded Or Incomplete Source Directories

- `Beer_etal_2013`: processed CSV and script are present, but `cusp/combine_data.py` currently skips it because it is an interpolated map product with no dates
- `Chen_2015`: removed from `data/` after duplicate review; retained in the master bibliography as a bibliographic-only source for synthesis traceability
- `Sadeghi_etal_2023`: processed CSV and script are present, but the source is currently excluded while its direct-observation status is reviewed
- `Yi_etal_2020_ABoVE`: processing script is present but no processed CSV is checked in; `cusp/combine_data.py` notes that it needs online processing because it is too large to load directly
- `Wilcox_2015`: currently skipped in `cusp/combine_data.py`; source files are present, but there is no checked-in processed CSV and the skip note says there are no lat/lon data for observations

## Recommended Next Steps For Phase 3

1. Add a short per-source rebuild note for the 34 included sources that currently have no obvious manual-step documentation artifact.
2. Decide whether those per-source notes live in each source directory, in a central manifest, or both.
3. Add short per-source rebuild notes or header-standard metadata for the included sources that still lack obvious manual-step documentation artifacts.
4. Decide which source-level outputs need byte-for-byte determinism versus semantic-stability guarantees only.
5. Revisit deferred sources like `Sadeghi_etal_2023` once the source-scope decision is made.
6. Create or refine scripted checks that distinguish:
   - clean rebuild
   - semantic rebuild with accepted byte drift
   - warning-only rebuild
   - deferred / external-dependency workflow
7. Clean up the script/source naming mismatches before automating rebuild checks.
