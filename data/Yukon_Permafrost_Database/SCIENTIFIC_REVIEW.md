# Scientific profile audit and deterministic recommendation

Audit date: 2026-11-03. Scope is scientific screening only; no production source files changed.
Archive: `../geotech.zip`, provider export 2025-09-21, SHA256
`c2f4b3069289646f939aa1117a41b4017ca2730d05cd3e655341cc2ce5443dc9`.

## Main actionable result

Recommend the 46 spatially consistent explicit late-summer thaw observations plus
646 additional August/September frozen-profile upper bounds = **692 site-level
observations**, before cross-source deduplication, under the rules below.
This is inference from logged frozen material in the summer thaw season, not
proof from two complete years of temperatures. Keep release clearance needs_review.

1. Join native SITE_ID exactly. Preserve PF_PERMAFROST_DESC.ID and all source
   fields supporting the selected observation. Group by native site, not proximity.
2. Exclude every KZK site from automatic processing; see verified source mismatches.
3. Parse START_DATE explicitly as Oracle `DD-MON-YY`; preserve original START_DATE,
   END_DATE. Do not permit Python's automatic two-digit-year pivot to create future
   years. Do not repair `31` to 1931 without evidence: four such dates exist in the
   broader location table, all outside the profile subset. Missing-profile dates
   occur at 72 sites, all KZK; no non-KZK missing-date recovery is needed.
4. Convert documented NAD83 UTM EPSG:26900+zone to WGS84. Compare with supplied
   decimal coordinates geodesically. Hold contradictions >10 m for original-report
   review. This is an audit threshold, not a claimed positioning accuracy. Preserve
   both representations and delta. Do not silently change UTM zones.
5. Prefer explicit SURFACE_THAW with comments identifying seasonal depth to
   permafrost or permafrost at the boundary, valid positive depth <= HOLE_DEPTH,
   and August/September date. 48 before spatial QA, 46 retained. Use measured
   thaw_depth; pf_depth follows existing CUSP near-maximum-thaw convention, with
   limitation that date-specific August/September thaw is not proven annual ALT.
6. For additional summer profiles: date August 1 through September 30; recognized
   frozen/ground-ice token (case normalized), excluding partial-only FX; valid
   0 <= TOP_DEPTH <= BOT_DEPTH; 0 < BOT_DEPTH <= min(10 m, HOLE_DEPTH); no row-local
   seasonal/possible/probable/may-be/likely wording; no X/frozen interior overlap.
   Select the shallowest qualifying BOT_DEPTH as the conservative upper bound
   of permafrost-top depth. Use pf_observed=1 with blank exact pf_depth/thaw_depth,
   positive upper-bound observation extent and registered UB/PA flags. Preserve
   all candidate intervals, including the selected row ID, in provenance.
   Bottom is deliberately conservative: coding intervals can begin below the
   actual frost table or simply delimit lithology; neither their first top nor
   their bottom is automatically an exact permafrost top.
7. Existing source-labelled permafrost rows in other seasons can support a second
   expansion, selecting the permafrost-labelled interval rather than shallow
   seasonal frost. Explicitly uncertain PF wording remains review-only. Do not
   infer perennial freezing merely because a winter interval exceeds 3 or 5 m:
   neither is a universal maximum seasonal-frost depth.
8. No universal profile/hole-depth rounding tolerance is needed. Strict <= keeps
   alternative valid rows and exposes bad rows. Any tolerance must be separately
   justified from native reporting precision and counted in a sensitivity table.

## Reproducible outputs and counts

Run with the repository environment:
`D:/Research/Miniforge3/envs/cusp/python.exe runs/yukon_candidate_20261103/deep_geotech/audit_profiles.py`
then `detail_checks.py`, `candidate_tiers.py`, `summer_bounds.py` in this folder.
All parsing/loops deterministic; base inventory uses only Python stdlib.
Coordinate comparison additionally uses installed pyproj 3.8.0, WGS84 geodesics.

- 15,436 unique locations; 6,531 PF description rows; 3,061 profile sites.
- 2,989 profile sites dated; 72 undated, all KZK.
- 2,829 profile sites have a valid frozen interval after case normalization;
  666 are August/September; 659 of those have no SURFACE_THAW.
- `summer_bound_candidates.csv`: 653 sites satisfy summer-bound rules before
  spatial QA; 651 retained; 2 spatial conflicts; zero interior X/frozen conflicts
  and zero reversed end/start date ranges in that candidate set.
- Of 651 summer bounds, 5 also have retained explicit SURFACE_THAW, so additional
  summer bound contribution is 646. 248 selected bottoms exceed 3 m; 39 exceed 5 m.
- `candidate_tiers.csv` is a separate wider screen (explicit PF any season,
  no 10-m-bottom cap). Its disjoint accounting: A exact thaw 46; B explicit-PF
  bounds 136; C other summer frozen bounds 634; D explicit non-detection 1;
  exclusions ambiguous/seasonal 2,105, hole depth 31, spatial 22, reversed date 9,
  KZK 77. Total 3,061. Do not confuse this wider screen with final 692 summer set.
- 173 sites match positive-looking permafrost wording before stronger uncertainty
  and negation QA: 156 dated, 17 undated. Text searches are screening aids only.
- 44 incomplete/invalid PF intervals: 2 inversions plus 42 missing endpoint rows.
  The 651 retained summer candidates use valid rows. `invalid_interval_rows.csv`
  is the complete excluded-interval evidence.

## Absence: what the data actually support

`X` in PF_GR_ICE_DESC explicitly means material not frozen. A missing PF row does
not mean absence. **Zero** profiles have continuous X coverage from 0 m through a
positive HOLE_DEPTH without frozen evidence. Fifteen sites have X and no recognized
frozen code, but some have possible-frozen text or isolated sample intervals.

One explicit non-detection is GINT_W14101360 TP04 (2009-12-02): 0-0.5 m seasonally
frozen, 0.5-2.0 m X with comment `unfrozen - no permafrost encountered in testpit`.
HOLE_DEPTH is 3.5 m, inconsistent with the logged thaw/frost profile ending at2m.
A conservative non-detection can be represented only to **200 cm**, the described
profile reach, with depth fields blank and PB/provenance; do not use 350 cm.
This is independent of the summer presence tranche.

Three possible whole-profile-X followups, GINT_W14103088 BH12-06/07/08, log X from
0.05 m to the hole bottom (10.7/9.1/9.1 m) in October 2012. The 5 cm surface gap
means they fail the strict continuous-from-zero rule. Do not promote from the X
code alone unless the original logs justify excluding the upper organic horizon.
Other X-only profiles are isolated samples; maximum sample depth is not a full
profile non-detection limit.

## Spatial evidence and limitations

14,473 locations have usable UTM fields: median geodesic decimal-vs-transformed
coordinate discrepancy 0.139 m; 73 >10 m, 57 >100 m, 40 >1 km. Among 2,972 PF sites
with usable UTM: median0.130 m; 10 >10 m, 8 >100 m, 1 >1 km.
Many supplied decimals therefore appear computed from the same UTM source;
this is an inference, not a documented datum declaration for those decimals.
NAD83 and WGS84 frame/epoch uncertainty is much smaller than the glaring outliers
but can still matter at metre precision; reported decimal digits are not accuracy.

Explicit-thaw coordinate conflicts:
- GINT_1240200-TH01: 441.7909708 m.
- GINT_1240200-TH07: 160.3791908 m.

A major profile outlier is GINT_209-3705 BH04: zone8 supplied, transformed longitude
-133.4294 versus provided -139.4294, ~292.9 km discrepancy. A six-degree zone error
is plausible, but choosing either representation without the report would invent
location provenance. Native site coordinates should remain unchanged in raw data.
Twelve recent YGS profile sites lack complete UTM; direct GPS/Avenza decimal
coordinates may still be usable with a declared datum approximation, but none
enters the 651 summer-bound set. Do not treat noUTM as automatic badGPS evidence.

3025/3061 profile locations have blank COORD_ACQ. Methods are also incompletely
populated (2805/3061 blank HOLE_TYPE). Preserve equipment and hole type; use
borehole/pit canonical mappings only where justified, and approximate-method flag
otherwise. Do not label every frozen-ground interval a core observation.

## KZK: primary-source evidence for holding all 77 profiles

Primary government-hosted report:
https://emrlibrary.gov.yk.ca/minerals/MajorMines/kudz-ze-kayah/project-proposal-2017/appendices/C-3-geotechnical-site-characterization-summary.pdf
Knight Piesold, report table B.1, printed Dec16/2016 (PDF table page labelled B-1/1of5).
The table distinguishes Permafrost Depth from Active Layer / Seasonal Permafrost.
Web extraction verified these mismatches against raw database rows:
- KZK_TP 104: raw SURFACE_THAW3.6m exceeds hole2.7m; source has seasonal depth0.30m.
- KZK_TP 105: raw SURFACE_THAW5.6m exceeds hole4.0m; source PF depth3.60m.
- KZK_TP 106: raw SURFACE_THAW3.8m versus source PF depth5.60m.
These are upstream transcription/row-alignment concerns; a date-year guess cannot
repair them. No KZK year recovered from site names is recommended for this export.
The `95`/`96` naming appears campaign-like but is not independently sufficient
for season, exact date, or correction of source values. `TP 103` has no year at all.

## Comparison with CUSP practice

- Jorgenson_Kanevskiy_2025 explicitly excludes ALF/seasonal frost and only uses
  definite cryostratigraphic horizons when mapping permafrost depth. This supports
  rejecting shallow winter frozen intervals and preserving explicit PF context.
- Hanston_etal_2024 leaves pf_depth blank for midsummer probe observations and
  flags an inferred state/limit convention. Its numerical threshold is specific
  to Teller/Kougarok and should not be imported into Yukon.
- CALM and Moore_et_al_2025 interpret source ALT values as presence with documented
  date approximation. This supports the source-labelled late-summer thaw tranche,
  but does not turn every Yukon SURFACE_THAW value into ALT.
- Smith_Burgess_2000/2002 use midpoint-year dates; comparisons must use native
  campaigns/periods rather than exact matching of assigned calendar days.

Required overlap audit remains separate: Smith/Burgess Yukon boreholes, CALM
Dawson/Teslin/Beaver Creek, Fisher Whitehorse. Spatial proximity alone is not a
supported reason to remove independent geotechnical holes or repeated years.

## Checks and remaining decisions

Archive hash and inventory stable. Candidate accounting sums to3061; frozen codes
are case normalized; no inferred false absences from missing PF rows; all selected
summer bound depths positive and <=10m and source holedepth; X/frozen overlap
checked by interval interiors rather than common boundary endpoints.

The main scientific inference requiring prominent metadata is summer-frozen
material => probable permafrost. August/September reduces seasonal-frost ambiguity
but cannot establish two-year persistence. UB/PA flags and retaining source interval
provenance make that assumption explicit. Single-year winter deepfrozen candidates
without source PF wording should remain outside this tranche.
