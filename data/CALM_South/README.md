# CALM-South Ingestion

Tracking: [issue #36](https://github.com/jonschwenk/cusp/issues/36).
Status: ingestion finalized with explicit maintainer authorization on 2026-10-05;
`release_clearance = "approved"`, `permission_basis = "other"`.
The original workbook is publicly downloadable, but an explicit reuse license
was not found. This records the maintainer's decision after review, not a provider
permission grant or an inferred license. The related Figshare extract's CC BY 4.0
license does not automatically apply to this original workbook.

## Source And Reproduction

The original [CALM South Summary Data workbook](https://www2.gwu.edu/~calm/data/CALM_S_Summary.xls)
was retrieved on 2026-10-05. `input_manifest.json` records URLs and SHA-256
checksums for the unchanged workbook and metadata evidence snapshots.
`site_overrides.json` records the rationale and references for each coordinate
or method lookup. The processor runs offline using `xlrd` from CUSP's optional
`source-processing` dependencies.

From the repository root:

```powershell
python data/CALM_South/process_calm_south.py
```

## Accounting

The workbook has 37 registered sites and 36 annual columns (1990-2025), producing
1,332 site/year cells. `processing_audit.csv` preserves all cells and decisions:

| Decision | Cells |
| --- | ---: |
| Positive exact annual ALT retained | 426 |
| Explicit lower-bound annual ALT retained | 11 |
| Missing or dash entries excluded | 893 |
| Zero ALT deferred | 2 |
| Total | 1,332 |

The processed table contains **437 observations at 31 sites**, with source year
labels 1997-2025, in Antarctica and Argentina. Methods: 323 temperature-derived,
107 probing, and 7 unknown. These are annual site summaries, not raw grid-node
measurements or dense temperature time series.

## Interpretation And Review

- Depths are centimeters. Exact ALT becomes both `thaw_depth` and `pf_depth`.
- Nine Granite Harbour `90+` values and two Livingston/Ramos Col `>130` values
  remain lower-bound observations: presence is not established within the stated
  limit, `obs_limit` is populated, and both exact depths are null. CALM's Granite
  Harbour metadata independently documents temperature monitoring to 90 cm.
- A25 2015 and A7 2018 zeros are not interpreted as absence without supporting
  observation limits. They remain visible in the audit.
- Source year is preserved. February 1 is a flagged summer placeholder, not a
  reported survey date or an assertion about whether a season spans two years.
- Six coordinate lookups are explicitly flagged. Molodyozhnaya's west/east error
  is corrected using native GTN-P station metadata. Invalid DMS at four other
  sites and Signy/Bertsen's coarse longitude are resolved using documented
  primary or versioned secondary metadata; these are representative locations.
- SA2C's disagreement among coordinate sources remains unresolved. The workbook
  location is retained and flagged. Seven Larseman Hills observations keep an
  unknown method rather than guessing which instrument generated their ALT.
- Composite method codes use documented site assignments with approximation
  flags. In particular, Rothera keeps the workbook's temperature/borehole method
  rather than adopting Figshare's conflicting probing label.

## Overlap

All 270 positive southern site/year observations in Figshare version 1 appear
here and agree within 1 cm. They are excluded by
[`Streletskiy_2026`](../Streletskiy_2026/README.md), retaining this original
workbook as the observation source. This workbook adds 156 positive site/years
and 11 bounds beyond those 270 values, including 14 positive values in 2025.
Existing Northern Hemisphere `CALM` and `PERMOS_2024` observations are unchanged.

A 1 km same-calendar-year screening against the pre-ingestion CUSP table found
five nearby NCSS soil-pit rows at four southern monitoring site/years. They are
different methods and field records, not duplicate annual thermistor summaries,
and were retained. Proximity is a review aid, never a deletion rule.

The maintainer authorized these documented coordinate, year, method, and
bound interpretations. The two zeros and SA2C coordinate disagreement remain
unresolved, and the original-workbook license remains unspecified. None is
silently repaired by approval. Finer-scale provider files are optional follow-ups;
author contact is not required to retain the accessible annual summaries.
Optional provider leads have separate issues linked in the
[Streletskiy ingestion notes](../Streletskiy_2026/README.md#future-provider-leads).
No official release export was changed.
