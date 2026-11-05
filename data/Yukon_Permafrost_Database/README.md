# Yukon Permafrost Database

Issue [#43](https://github.com/jonschwenk/cusp/issues/43). Prepared 2026-11-03.
**Release clearance: `approved` for v1.3, 2026-11-05.** Following the staged
973-observation report, the maintainer authorized committing this ingestion,
incrementing the dataset version, and pushing its commit and tag. Documented
assumptions, flagged bounds and exclusions remain part of the approved inclusion.

## Source and reproducibility

Yukon Geological Survey (2026), Yukon Permafrost Database, Government of Yukon,
[portal](https://data.geology.gov.yk.ca/permafrost). Both provider exports are
dated **2025-09-21**, retrieved 2026-11-03. The portal's nominal download sizes
and historical documentation counts differ from the inspected archive contents.
`raw_manifest.json` records the pinned archive and processor-input hashes.

Contains information licensed under the Open Government Licence - Yukon.
See `permission_evidence.json` for the catalogue, attribution, terms link and
third-party-rights qualification. Original consultants, clients and operators
remain in row provenance. Maintainer approval is separate
from the provider reuse terms and does not extend them to unlicensed third-party material.

Normal processing is offline in the CUSP environment:

```powershell
python data/Yukon_Permafrost_Database/process_yukon_permafrost_database.py
python data/Yukon_Permafrost_Database/audit_unknown_accuracy.py
```

The 3 MB original geotechnical ZIP is preserved. The 233 MB temperature ZIP
is retained locally and ignored; download it through the
portal Downloads tab (Temperature Sensor Dataset / CSV). To regenerate the
checked compact evidence from its **32,722,705 raw records**:

```powershell
python data/Yukon_Permafrost_Database/summarize_temperature.py --archive runs/yukon_candidate_20261103/temperature.zip --output-dir runs/yukon_thermal_recheck
```

The helper checks the original archive hash before streaming. The raw stream has
32,476,218 ground-temperature and 246,487 air-temperature rows; 4,912,348 ground
rows are outside the chosen point-sensor/subsurface/10-m support and 8 are invalid
or sentinel temperatures. The remaining 27,563,862 readings produce 7,979 annual
station/depth groups, preserving actual raw maxima, distinct-day coverage,
instrument accuracy, provider, method, comments and daily masks. It uses neither
annual means as detection evidence nor a fabricated thermal maximum.

The compact original station/provider/method and provider annual-summary tables
are retained. Provider annual summaries are used only for overlap screening,
not permafrost inference. `thermal_annual_audit.csv` is the reproducible compact
evidence used by the normal processor; hashes protect it from silent changes.

## Accounting and interpretation

| Accepted tier | Rows | Representation |
|---|---:|---|
| Explicit thaw boundaries | 46 | Dated August/September `thaw_depth` and `pf_depth`, metres to cm |
| Source-labelled permafrost intervals | 129 | Presence upper bound; exact depths blank; `UB` |
| Other late-summer frozen intervals | 624 | Presence upper bound; seasonal interpretation explicitly flagged `UB;PA` |
| Two-year temperature evidence | 170 | Presence upper bounds at 28 stations, 2009-2020; `UB;TI;DA;SS` |
| Explicit testpit non-detection | 1 | 200 cm observed extent, not the 350 cm hole metadata; `LB;PB` |
| Continuous explicitly unfrozen profiles | 3 | Observed contiguous reach 1580, 1100 and 1550 cm; `LB;PB` |
| **Total** | **973** | **969 presence, 4 bounded non-detections** |

The geotechnical archive has 15,436 sites, including 3,061 with frozen-ground
description profiles. The processor retains 803 profile-site investigations and
records all 2,258 other profile-site decisions in `ingestion_audit.csv`.
Each borehole investigation produces at most one row, despite multiple logged
layers. All raw selected-profile rows and location fields remain in provenance.
Source depths are not silently corrected. Valid intervals must have ordered
endpoints within the stated hole depth; invalid rows remain visible in provenance.

The 170 thermal rows are selected from 435 qualifying sensor-year endpoints;
265 deeper qualifying sensors support the same station-year and are not emitted
as additional observations. All 7,979 decisions are audited. Later-year summaries
share their earlier-year thermal support with adjacent pairs; they are repeated
monitoring evidence, not independent samples.

### Accepted scientific assumptions and limitations

- Source numeric thaw values explicitly naming permafrost take precedence. They
  are instantaneous field depths, not proven annual maximum ALT. No generic
  `SURFACE_THAW` field is accepted without supporting semantics.
- Additional source-labelled intervals are bounded at a valid interval bottom,
  within 10 m. A lithological/sampling interval edge is not treated as the exact
  top of permafrost. Ambiguous, negated and explicitly seasonal wording is held.
- August-September frozen material is interpreted as permafrost
  (`PA`), following CUSP's thaw-season field conventions. Residual seasonal frost
  remains possible. No universal winter 3-m or 5-m threshold is imposed.
- Thermal presence requires two consecutive calendar years at the same depth,
  each with at least 95% distinct-day coverage, no missing run longer than 7 days
  including endpoints, and all valid raw readings colder than negative documented
  sensor accuracy. Provider/method changes and comments are held. This is a
  conservative inference despite missing days, not proof of uninterrupted cold.
  The shallowest qualifying sensor at or above 10 m supplies a bound, not ALT.
- Negative subsurface sensor depths become positive cm. Above-ground sensors,
  `-999` records, interval summaries and non-ground observation types are excluded.
- The native NAD83 UTM transforms to WGS84; conflicting decimal coordinates over
  10 m are held. For documented GPS/Avenza positions without UTM, source decimals
  are treated as approximate WGS84 and flagged `CF`. This admitted one 2023
  source-labelled bound and three continuous-unfrozen profiles. The coordinate
  digits are not claimed to be survey accuracy.

## Deliberate holds and sensitivity

`SCIENTIFIC_REVIEW.md` preserves the independent deeper audit. Its initial
692-row summer recommendation predates the final explicit-PF, thermal and
2023-profile expansion above; the processor, tests and summary define final counts.

- All **77 KZK profiles** are held: checked original-report values conflict with
  exported thaw values, including values exceeding hole depth. No missing date
  is guessed from a borehole name.
- Ten coordinate contradictions and nine reversed investigation-date ranges are
  held. Two of the original 48 obvious late-summer candidates fail spatial QA.
- An arbitrary depth in winter is not sufficient evidence of perennial freezing.
  A missing PF-description row does not mean absence. Isolated `X` intervals do
  not establish no permafrost throughout an unobserved hole.
- Unknown instrument accuracy remains excluded. `unknown_accuracy_sensitivity.csv`
  identifies **66, 41 and 20 hypothetical station-years** under assumed margins
  0.25, 0.5 and 1.0 C respectively; these are overlapping sensitivity scenarios,
  not additional accepted observations or calibrated error estimates.
- Stewart Crossing is not ingested: source metadata says Undetermined; its
  available 4-m raw annual maxima in 2016-2019 are 7.99-8.80 C, coverage is
  incomplete in the endpoint years, and accuracy is undocumented. A warm point
  sensor does not establish whole-profile permafrost absence.

## Overlap

`OVERLAP_REVIEW.md` and the two summary JSON files preserve provenance and
sensitivity checks. No deletion is justified. All 73 original thaw candidates
are more than 20.95 km from existing CUSP observations; 44 PF-profile sites have
neighbors within 2 km, but none shares the existing source observation period.
Comparisons use original Smith/Burgess periods and CALM years, not placeholder dates.

Some Shakwak/YGS thermal station-years are near CALM_C24. The source boreholes
are distinct from CALM's probe grid/transect; retain both resolutions and mark
the **86 retained shared-period thermal rows `DO`**. Do not treat these as
independent regional replicates. Reproduce the comparisons, excluding this new
source from its own comparison inputs, with:

```powershell
python data/Yukon_Permafrost_Database/audit/audit_thermal_overlap.py
```

Outputs go to ignored `runs/yukon_overlap_recheck/`. Detailed original local audit
artifacts remain under `runs/yukon_candidate_20261103/`.

## Validation and review

Pinned counts and semantic safeguards are tested in
`tests/test_yukon_permafrost_database.py`. Source metadata, canonical and aggregate
QC, full tests and strict docs are included in the staging validation report.
The original 2026-11-03 staging validation in `VALIDATION.md` is historical;
final release validation is recorded in the v1.3 release notes. Published
historical archives must not be overwritten.

Scientific and overlap reviews used deep_reviewer agents (requested
gpt-6.1-sol/high); focused tests used economical_worker (requested
gpt-6-luna/high). Effective runtime settings were not independently confirmed.
