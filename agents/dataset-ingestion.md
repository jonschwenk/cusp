# CUSP Dataset Discovery and Ingestion Runbook

This runbook preserves the working process for finding candidate datasets,
assessing whether they belong in CUSP, and carrying a selected source through a
complete, reviewable ingestion. It is written for coding agents working with a
CUSP maintainer.

Use this document together with, not instead of, the repository's schema and
maintainer documentation. Source-specific scientific judgment should always be
made explicit in code, metadata, and the final handoff.

## Roles and decision boundaries

The maintainer owns these decisions:

- whether a candidate is scientifically appropriate for CUSP;
- whether uncertain source semantics have been interpreted correctly;
- which record should be retained when overlap cannot be resolved objectively;
- whether reuse permissions are adequate; and
- whether a processed source is approved for a public release.

The agent is expected to:

- investigate the candidate in detail;
- identify access, provenance, licensing, and citation information;
- inspect the actual files and measurement semantics;
- assess overlap with sources already in CUSP;
- recommend proceeding, deferring, or declining;
- implement the processor and metadata when the source is suitable;
- perform source-level deduplication with auditable rules;
- run validation and tests; and
- report every material transformation, exclusion, uncertainty, and remaining
  decision.

Do not force an ingestion merely because a candidate was proposed. A careful
recommendation that a source is out of scope, inaccessible, redundant, or too
ambiguous is a successful outcome.

New sources must use `release_clearance = "needs_review"`. An agent must never
approve a source for release on the maintainer's behalf.

## Ways to start the workflow

### Discovery mode

When asked to find new data, search for primary observational datasets and the
papers or repository records that document them. Prefer canonical publisher,
DOI, institutional repository, and data-archive pages over mirrors.

For each plausible candidate, report:

- title, authors, year, DOI, and canonical data URL;
- geographic and temporal coverage;
- observation type and measurement method;
- approximate record count and available file formats;
- whether coordinates, dates, depths, and detection limits appear usable;
- license or other reuse basis;
- likely overlap with existing CUSP sources; and
- a recommendation with the main reason for or against ingestion.

Unless the maintainer has already authorized end-to-end ingestion, stop after a
shortlist and let the maintainer select candidates. Do not download or commit a
large collection merely to determine whether it might be useful.

### Candidate handoff mode

The maintainer can start a detailed review with a prompt like this:

```text
Follow agents/dataset-ingestion.md for this candidate.

Candidate URL or DOI:
Tracking issue, if any:
Why it may fit CUSP:
Known permission or access information:
Known overlap with existing sources:

Investigate it in detail. If it is suitable and no maintainer decision is
needed, ingest it end to end, including processing-level deduplication and
validation. Leave release clearance as needs_review.
```

The repository's dataset-candidate issue form at
[`../.github/ISSUE_TEMPLATE/dataset_candidate.yml`](../.github/ISSUE_TEMPLATE/dataset_candidate.yml)
can hold the same intake information.

## Phase 1: suitability review

Read the source landing page, paper, supplement, repository metadata, README,
data dictionary, and license or terms before writing a processor. Inspect the
actual downloadable files rather than relying only on an abstract.

Answer these questions in a candidate assessment:

1. Are these direct, geolocated near-surface permafrost observations rather
   than a modeled product, interpreted map, or context raster?
2. Can individual observations be tied to usable coordinates and a date or a
   defensible date representation?
3. Does the source report a CUSP-compatible observation, such as permafrost
   presence or absence, active-layer or thaw depth, frost-table or permafrost
   depth, or a related probe, pit, core, auger, borehole, or field-geophysical
   measurement?
4. Is the measurement basis clear enough to distinguish observed permafrost
   from an observation that simply did not reach permafrost?
5. For absence records, is a positive observation limit available, or is the
   record explicitly a visual interpretation that can be flagged as such?
6. Are units, coordinate reference system, missing-value codes, identifiers,
   and temporal fields documented or recoverable without guesswork?
7. Is there a stable citation and provenance trail?
8. Can CUSP legally redistribute the processed observations, or must release
   remain deferred while permission is clarified?
9. Is the dataset original, a synthesis, or a republished subset of data that
   CUSP may already contain?

Classify the result as one of:

- **Proceed:** in scope, sufficiently interpretable, and technically
  ingestible.
- **Proceed with documented limitations:** useful records can be represented
  honestly, but limitations or exclusions must be prominent.
- **Needs maintainer decision:** a scientific, permission, or overlap choice
  cannot be resolved from the source material.
- **Defer:** potentially useful, but files, metadata, permission, or source
  clarification are not yet available.
- **Out of scope:** fundamentally incompatible with CUSP's observational data
  model.

Do not begin a full implementation until the source reaches one of the two
proceed states, either directly or through a maintainer decision.

## Phase 2: source audit

Create a concrete inventory before transforming the data:

- downloaded files, archive version, checksums when useful, and retrieval date;
- sheets, tables, layers, and raw row counts;
- coordinate fields, CRS, precision, and known spatial uncertainty;
- date fields, precision, seasons, date ranges, and placeholder dates;
- source identifiers for sites, plots, transects, profiles, and observations;
- methods and what each measured depth physically represents;
- units and conversion rules;
- missing-value and sentinel codes;
- presence, absence, refusal, bedrock, water, and maximum-probe-depth semantics;
- duplicate-looking records and possible provenance from older datasets;
- fields that should be retained for traceability even if they are not part of
  the canonical release; and
- records that cannot be interpreted without an explicit assumption.

Preserve the raw source faithfully. Do not silently repair or overwrite source
files. If redistribution, file size, credentials, or download mechanics prevent
raw files from being committed, document the exact retrieval and manual steps
in the processor metadata.

Before assigning a new source key, search the current source registry,
processed files, source metadata, citations, and duplication notes:

- [`../cusp/canonical_observation_schema.json`](../cusp/canonical_observation_schema.json)
- [`../data/source_metadata.csv`](../data/source_metadata.csv)
- [`../data/source_duplication_notes.csv`](../data/source_duplication_notes.csv)

## Phase 3: overlap and deduplication plan

Deduplication is part of scientific source processing, not a generic cleanup
step. Write down the overlap hypothesis and matching rules before dropping
rows.

### Distinguish different kinds of apparent duplication

- **Exact duplicate:** the same observation is repeated within a file or source.
- **Republished observation:** a synthesis or later product contains a copy of
  an observation from an original dataset.
- **Alternate representation:** the same site and campaign appears in two files
  with rounded coordinates, different column names, or different levels of
  detail.
- **Repeated measurement:** the same site was measured on another date, in
  another year, at another depth, or with another method. This is generally a
  distinct scientific observation.
- **Dense spatial sampling:** nearby points from a transect or geophysical
  survey may be intentionally correlated but are not duplicates.
- **Uncertain overlap:** records resemble one another but provenance or
  precision is insufficient to establish identity.

Never remove records solely because they are geographically close. Spatial
proximity can be evidence in a source-specific comparison, but it must be
combined with appropriate identifiers, dates, methods, values, contributor
information, or documented provenance.

The exact-duplicate handling in `cusp.build` is only a final safety net. It does
not replace source-level overlap analysis and must not be expanded into a broad
cross-source proximity filter.

### Build an auditable comparison

1. Identify likely parent or overlapping CUSP sources from the candidate's
   citations, contributor names, site identifiers, coordinates, dates, and
   descriptions.
2. Compare raw or processed records using the strongest available combination
   of source IDs, site or transect IDs, contributor, date or year, coordinates
   with a justified tolerance, method, and measured value.
3. Inspect matched and unmatched samples manually. Quantify how sensitive the
   result is to rounding or date precision when those matter.
4. Establish a retention rule. Normally prefer the original direct source over
   a synthesis, or the representation with clearer provenance, native
   coordinates, dates, methods, and observation limits. Ask the maintainer when
   neither representation is clearly preferable.
5. Remove only rows supported by the documented rule. Retain uncertain records
   with an appropriate limitation or quality flag unless the maintainer decides
   otherwise.
6. Add expected-count assertions or equivalent tests so a changed upstream
   file fails loudly instead of silently changing the deduplication result.
7. Record the compared source, matching fields and tolerances, number removed,
   retained representation, assumptions, and unresolved overlap in the process
   script metadata and source duplication notes as appropriate.

For useful local patterns, inspect the current implementations in:

- [`../data/Talucci_2024/process_talucci_2024.py`](../data/Talucci_2024/process_talucci_2024.py)
- [`../data/Ruess_2025/process_ruess_2025.py`](../data/Ruess_2025/process_ruess_2025.py)
- [`../data/Pastick/process_pastick.py`](../data/Pastick/process_pastick.py)
- [`../data/Moore_et_al_2025/process_moore_et_al_2025.py`](../data/Moore_et_al_2025/process_moore_et_al_2025.py)

These are examples, not universal matching rules. Re-derive tolerances and
retention logic from each candidate's provenance and measurement design.

For dense GPR or similar surveys, consider
`data_utils.aggregate_gpr_points()` using a scientifically justified grouping
and distance. Keep independent survey dates, years, transects, and methods in
separate groups. Resolve known republished observations before spatial
aggregation whenever the raw provenance permits it.

## Phase 4: implementation

Follow the current conventions in
[`../docs/maintainers/adding-data.md`](../docs/maintainers/adding-data.md) and
read nearby processors before creating files. A typical source directory is:

```text
data/Example_2026/
  raw files or documented retrieval inputs
  process_example_2026.py
  processed_example_2026.csv
```

### Processor requirements

- Make processing deterministic and rerunnable from the documented inputs.
- Prefer structured readers and explicit transformations over ad hoc text
  manipulation.
- Keep source-specific logic in the source processor rather than adding special
  cases to the global build.
- Preserve useful raw identifiers and provenance fields in the processed
  all-fields output.
- Convert coordinates to WGS84 longitude and latitude (`EPSG:4326`).
- Normalize dates to `YYYY-MM-DD` while documenting reduced precision or
  imputation.
- Normalize depths and observation limits to centimeters.
- Represent unknown values as nulls, not undocumented numeric sentinels.
- Populate at least `lon`, `lat`, `date`, `source`, `site_id`, `pf_observed`,
  `pf_depth`, `thaw_depth`, and `obs_limit`; include `method` whenever possible.
- Set `pf_observed = 1` when a numeric thaw or permafrost depth demonstrates a
  detection.
- Use `pf_observed = 0` only for an explicit non-detection with a positive
  `obs_limit`, except for supported visual interpretations marked with
  `quality_flag_visual_interpretation = True`.
- Leave canonical depth fields blank for absence records.
- Name quality flags `quality_flag_<flag>` and use definitions registered in
  [`../data/quality_flag_definitions.csv`](../data/quality_flag_definitions.csv).
- Add the source key and controlled vocabulary additions to
  [`../cusp/canonical_observation_schema.json`](../cusp/canonical_observation_schema.json)
  only when needed. Registry changes should be additive and narrowly scoped.

Do not discard a record just to make validation pass. Either represent it
honestly with a documented flag or limitation, or exclude it for a clear,
reported reason.

### Process metadata

Use the repository's TOML process-script header format described in
[`../docs/maintainers/process-script-header-guidelines.md`](../docs/maintainers/process-script-header-guidelines.md).
At minimum, make these topics explicit:

- metadata schema version and source key;
- `release_clearance = "needs_review"`;
- permission basis and evidence known so far;
- original author and last substantive update;
- source dataset citation and stable URL;
- processing assumptions;
- temporal and spatial handling;
- manual steps and external dependencies;
- known limitations; and
- all overlap and deduplication decisions.

Follow
[`../docs/maintainers/source-release-clearance-guidelines.md`](../docs/maintainers/source-release-clearance-guidelines.md)
for permission terminology. Do not manually edit generated
`PROCESS_SCRIPT_METADATA.csv` content.

### Tests and safeguards

For a nontrivial interpretation or overlap rule, add a focused test or a small
fixture when practical. At minimum, the processor should assert important row
counts and deduplication counts, along with invariants whose failure would
indicate that the upstream data changed.

Useful invariants include:

- raw rows equal retained rows plus exclusions by reported reason;
- expected overlap matches are stable;
- no invalid coordinates or impossible depths remain;
- presence and absence semantics satisfy the canonical rules; and
- independent repeat observations were not collapsed.

## Phase 5: validation

Run the source processor and inspect both summary counts and representative
rows. Do not rely only on a successful exit code. Check coordinate ranges,
dates, depth units, null patterns, methods, state or region labels, source IDs,
quality flags, and raw-to-processed accounting.

Use the repository's active Python environment and run the relevant commands:

```powershell
python data/Example_2026/process_example_2026.py
python -m cusp.generate_process_script_metadata --check --strict
python -m cusp.build
python -m cusp.qc validate-observations
python -m cusp.aggregate
python -m cusp.qc validate-aggregated
python -m pytest -q
python -m cusp.readme_tracker --check
python -m mkdocs build --strict
git diff --check
```

Some generated metadata may need to be regenerated before its `--check` mode
can pass; follow the command help and existing maintainer workflow. Run the
widest relevant validation after generation.

Review the final diff and generated artifacts. Expected source, schema,
metadata, documentation, and aggregate changes are acceptable. Investigate
unrelated changes rather than reverting user work. Do not publish a release or
change source clearance unless explicitly asked.

## Phase 6: maintainer handoff

Finish with a concise ingestion report containing:

- **Recommendation:** proceed, defer, decline, or ready for maintainer review.
- **Source and version:** canonical citation, URL, retrieval date, and files.
- **Coverage:** places, dates, methods, observation types, and final row count.
- **Row accounting:** raw rows, retained rows, and exclusions grouped by reason.
- **Transformations:** coordinate, date, unit, presence/absence, and identifier
  handling.
- **Deduplication:** compared CUSP sources, matching rule, tolerance, counts,
  retained representation, assertions, and unresolved overlap.
- **Limitations:** ambiguities, approximations, quality flags, and records not
  represented.
- **Permission:** evidence found, current basis, and why clearance remains
  `needs_review`.
- **Verification:** commands run and their results.
- **Maintainer decisions:** every question still requiring human scientific or
  release judgment.

The handoff should give the maintainer enough information to review the source
without reconstructing the entire investigation from terminal history.

## Stop and ask the maintainer when

- access requires credentials or acceptance of terms not already authorized;
- redistribution rights or attribution requirements are unclear;
- an observation cannot be mapped to presence, absence, depth, or observation
  limit without inventing semantics;
- coordinate or date reconstruction would materially change scientific meaning;
- plausible cross-source duplicates cannot be distinguished from repeated
  measurements;
- two overlapping representations have no defensible retention preference;
- an upstream revision changes expected counts or deduplication behavior;
- ingestion requires a breaking canonical-schema change; or
- completing the task would overwrite unrelated work or require destructive
  repository operations.

## Authoritative references

- [What CUSP contains](../docs/getting-started/what-is-cusp.md)
- [Data caveats](../docs/getting-started/caveats.md)
- [Adding a dataset](../docs/maintainers/adding-data.md)
- [Process-script header guidelines](../docs/maintainers/process-script-header-guidelines.md)
- [Source release-clearance guidelines](../docs/maintainers/source-release-clearance-guidelines.md)
- [Canonical observation schema](../cusp/canonical_observation_schema.json)
- [Quality-flag definitions](../data/quality_flag_definitions.csv)
- [Dataset candidate issue form](../.github/ISSUE_TEMPLATE/dataset_candidate.yml)

If these references and this runbook diverge, follow the current schema and
maintainer documentation, then update this runbook in the same change so the
workflow remains trustworthy.
