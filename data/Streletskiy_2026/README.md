# Streletskiy 2026 Ingestion

Tracking: [issue #36](https://github.com/jonschwenk/cusp/issues/36).
Status: ingestion finalized with explicit maintainer authorization on 2026-10-05;
`release_clearance = "approved"`.

## Source And Reproduction

Source: [Streletskiy (2026), Figshare version 1](https://doi.org/10.6084/m9.figshare.32885756.v1),
`CALM_Sites_Data.csv`, file id 66270764, retrieved 2026-10-05, CC BY 4.0.
`figshare_metadata.json` preserves the repository version, citation, and license.
The related [paper](https://doi.org/10.1038/s43247-026-03824-1) is also a guide to
original providers, not the producer of all the underlying measurements.

Run from the repository root **after CALM-South processing**, with existing
processed `CALM` and `PERMOS_2024` tables present:

```powershell
python data/Streletskiy_2026/process_streletskiy_2026.py
```

The processor checks the raw version-1 SHA-256 and records every decision in
`processing_audit.csv`. It requires the reviewed working CALM-South table to
verify the southern source preference. These inputs are available in the
repository and are required to reproduce its overlap checks. No contact-only
provider files are required. The maintainer approved both ingestions after review;
that decision does not extend Figshare's license to the original CALM-South workbook.

## Accounting

| Decision | Rows |
| --- | ---: |
| Existing CALM depth agrees within 1 cm; keep CALM | 2,152 |
| Existing CALM depth disagrees; defer revision | 57 |
| Existing CALM bounded/nonexact depth; keep CALM | 3 |
| Southern annual ALT represented by original CALM-South | 270 |
| Missing or dash ALT | 801 |
| Zero ALT deferred | 2 |
| CH1 2022 PERMOS quality conflict deferred | 1 |
| New Northern Hemisphere observations retained | 214 |
| Total | 3,500 |

The 214 additions cover 24 sites and source years 2000-2024: France (38), Italy
(40), Mongolia (79), USA (53), and Russia (4). Methods: 210 temperature-derived
and 4 probing. Only annual observed ALT is imported; ERA5-Land climate fields,
trend estimates, and significance statistics are not CUSP observations.

## Interpretation And Deduplication

- Match normalized CALM site code and annual year labels, not proximity or the
  assigned September 1 placeholder. Keep every independent retained year.
- The existing PANGAEA-derived CALM source is retained for all 2,212 shared
  annual records. The audit preserves candidate values, original depths, bounds,
  states, observation limits, and method differences. Conflicting values are
  not declared exact duplicates and are not silently substituted.
- Match retained PERMOS `calm_id` and annual year as a further provider check;
  there are no additional direct matches among these candidate additions.
  Duplicate provider keys require review rather than silent set collapse.
- `review_exclusions.json` documents CH1 2022: the original COR_0287 PERMOS record
  has missing ALT and an unreliable-data comment. Figshare's 724 cm value is
  deferred; the nearby replacement borehole's 379 cm value remains separate.
- The two zero entries are not classified as absence. All 214 retained annual
  ALT values are positive and imply presence, with depths in centimeters.
- Dates are flagged year-only placeholders, coordinates are site-level, and
  methods are flagged site-level approximations. Original method labels and
  site/country identifiers remain in the processed table.
- Same-year screening within 1 km found three nearby Alaska soil-pit rows at
  two candidate site/years (Drew Point and Piksiksak). These independent records
  were retained; neither matching depth nor proximity establishes republication.

## Future Provider Leads

The six tracked leads below were reviewed on 2026-10-05 without author contact.
Ten public Crater Lake manual probes were prepared as
[`Crater_Lake_AERT_2024`](../Crater_Lake_AERT_2024/README.md), with site-level
coordinates and overlap flags; Jon Schwenk approved their inclusion in v1.2
on 2026-10-05.
The remaining native data and ERT interpretation were deferred or found
incompatible with CUSP; closed issues preserve public-file inventories,
interpretation concerns, and explicit conditions for revisiting them.

Annual observations already available in the original workbook or this synthesis
are ingested; obtaining contact-only native files is not a prerequisite. These
are optional opportunities for **additional detail or years**, not outstanding
requirements for this ingestion:

- [Limnopolar/A25 (#38)](https://github.com/jonschwenk/cusp/issues/38): grid-node and within-season probing may add spatial
  detail; confirm raw files and node coordinates before curating.
- [James Ross Island/JGM (#39)](https://github.com/jonschwenk/cusp/issues/39): [Hrbacek et al. (2025)](https://doi.org/10.1002/ppp.2274)
  has grid and temperature-derived ALT, with data available upon request. Twelve
  A27 annual summaries are already ingested through CALM-South. Revisit finer-scale
  records only if public files become available or are offered by the provider.
- [Morenas Coloradas (#3)](https://github.com/jonschwenk/cusp/issues/3): [Trombotto and Borzotta (2009)](https://doi.org/10.1016/j.coldregions.2008.08.009)
  describes monitoring extending before 2000. SA2A/B/C annual summaries are already
  ingested through CALM-South; revisit earlier or finer-scale records if a usable
  public observation table becomes available, without requiring author contact.
- [Cime Bianche (#40)](https://github.com/jonschwenk/cusp/issues/40): native borehole data may improve provenance;
  [related work](https://tc.copernicus.org/articles/18/3383/2024/) provides data on
  request. Sixteen IT2 annual observations (2008-2023) are already ingested through
  Streletskiy. Native profiles or extra years remain optional public-data leads;
  raw temperatures or geophysics need a documented depth interpretation.
- GTN-P's public metadata/data API is a useful discovery route, but the current
  southern holdings do not replace the full original CALM-South annual workbook.
- [Crater Lake A-ERT (#41)](https://github.com/jonschwenk/cusp/issues/41): the
  [Farzamian et al. (2024) study](https://tc.copernicus.org/articles/18/4197/2024/)
  links public field-geophysics files and ten dated manual probe measurements.
  The probes were prepared with site-level coordinates and component-to-summary
  overlap documented; ERT-derived depths remain deferred because their threshold
  and sensitivity choices require scientific review. Raw resistivity and
  inversion cells are not themselves CUSP observations.
- [Crater Lake 50 cm temperatures (#42)](https://github.com/jonschwenk/cusp/issues/42):
  a [public Zenodo archive](https://doi.org/10.5281/zenodo.15849051) includes
  16 located sensors. Single-depth temperatures alone do not yield exact ALT or
  permafrost absence; this is a low-priority suitability check that may add nothing.

No new public CUSP release was published. Existing official exports and all
pre-ingestion observation IDs were preserved.
