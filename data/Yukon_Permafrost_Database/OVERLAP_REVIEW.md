# Yukon cross-source overlap audit, 2026-11-03

Recommendation: keep the scientifically accepted new observations. No confirmed
republished observation and no defensible cross-source exclusion was found. This
is an overlap assessment, not approval of every raw profile's permafrost semantics.

## Inputs and reproducibility

Run `python runs/yukon_candidate_20261103/overlap/audit_overlap.py` and
`python runs/yukon_candidate_20261103/overlap/audit_thermal_overlap.py` from the repo.
Both use Python standard library only. The second refreshes the geotechnical audit.
The archive hashes and every processed input hash appear in `summary.json`; the
thermal hash appears in `thermal_summary.json`. The canonical snapshot has 80,264
rows. Comparison uses all existing processed files, including any rows subsequently
excluded by canonical build, so this is a conservative search rather than a claim
that every comparison row is released. Geographic envelope 58--71 N, 142--123 W
contains 1,946 comparison rows / 823 unique coordinates from 11 sources, including
77 Smith_Burgess_2000, 43 Smith_Burgess_2002, 340 CALM and 42 Fisher_2016 records.

`candidate_inventory.csv` preserves native project/consultant/client IDs and all
location fields. `existing_regional_sites.csv` lists existing identifiers and
aliases, locations, canonical dates and source periods. `pairs_within_2000m.csv`
records original file and row number, profile IDs, dates, coordinates, year ranges,
methods, values and coordinate acquisition metadata. `nearest_existing.csv` gives
the nearest comparison location for all 3,061 sites with PF-description profiles.
Global exact normalized identifier/alias comparison found no matches, including
after stripping the candidate GINT_ namespace prefix. Name similarity alone is
not a reliable identity test for local numeric or BH labels.

## Rules and precision

Great-circle distance uses a spherical Earth radius of 6,371,008.8 m. Screening
radii are 10, 50, 100, 500, 1,000 and 2,000 m; a 0.1-degree spatial bin with its
eight neighbors completely covers the 2-km radius at the maximum latitude.
These are sensitivity thresholds, not positioning-error estimates. Candidate
latitude is commonly exported at seven decimals and longitude at five, but
15,312/15,436 locations lack COORD_ACQ. The numerical digits can reflect coordinate
conversion and do not establish submeter accuracy. Smith/Burgess coordinates and
periods are heterogeneous compilations; long floating-point decimals also do not
establish positioning precision. The 2-km envelope comfortably exceeds rounding
of typical hundredth-degree or whole-minute coordinates, but cannot rule out gross
historical location errors or undocumented aliases.

Comparison uses the original Smith/Burgess `source_period`, including full-year
ranges and abbreviated endpoints, instead of requiring a candidate date to equal
the assigned July 1 midpoint. CALM is compared by annual source year rather than
assigned September 1; Fisher Whitehorse by 2013 rather than assigned August 31.
For geotech, the raw drilling start year is the campaign comparison year; this is
not assumed to establish a particular profile measurement day. SURFACE_THAW metres
are converted to centimetres for comparison at 1- and 5-cm tolerances. Interval
tops are not assumed to be ALT or permafrost depths. Proximity plus year/value
agreement remains a hypothesis until provenance and measurement support agree.

## Geotechnical result

All 73 positive SURFACE_THAW sites have zero existing observations within 2 km.
Their nearest comparison site is at least 20,951.910 m away. Therefore any subset
accepted on scientific grounds contributes observations with no identified
cross-source copies. Fifty-five have start dates; the 18 undated records remain
subject to date interpretation. This does not make all 73 ingestible.

For all 3,061 PF-description sites (73 thaw plus 2,988 other profiles), no pair
exists within 100 m. Seven sites are within 500 m, 13 within 1 km and 44 within
2 km; none shares a drilling year with the original period of an existing source.
Thus no existing-profile duplicate is supported by the available date evidence.

Considering all 15,436 locations, including 12,375 without PF-description rows,
119 are within 2 km. Three have same-period neighbors: YukonU_AH_1865.2_PS_R
(2014, 398.385 m from CALM_C24), YukonU_AH_1865.9_PS_R (2014, 853.291 m), and
YukonU_OCF_S1_2018_BH1_F (2018, approximately 687--850 m from Moore_et_al_2025
KT-2_KTurner / KT-3_KTurner transect observations). Those are unconfirmed spatial
and campaign associations, not thaw/profile duplicates. No same-period pair has
a comparable positive SURFACE_THAW value within either depth tolerance.

## Thermal locations and dependence

The separate thermal archive has 241 stations and 10,663 annual summary rows.
`thermal_station_inventory.csv` preserves all station metadata, stated location
accuracy, provider/method IDs, available annual-summary subsurface years and nearest
existing site. `thermal_pairs_within_2000m.csv` provides row-level evidence.
Annual coverage here excludes -999/sentinel temperatures, nonnegative depths and
years before 1950. Coverage does not assert complete years or establish permafrost;
the production processor must inspect raw records, uncertainties and completeness.

No thermal location lies within 100 m of an existing comparison point. At 500 m,
27 stations have neighbors and 26 have shared years; at 1 km, 32 have neighbors;
at 2 km, 34 have neighbors. All 26 same-year cases are the 25 `HPW_Shakwak_*`
stations and `YGS_BeaverCreek`, around CALM_C24 / Beaver Creek. Distances to the
CALM coordinate are 129--408 m; candidate reported accuracies are 5--10 m.
Shared years are 2010--2014. CALM_C24 reports mechanical probing at a 50-m grid
or transect (PI Edda Mutter); the candidate HPW/YGS stations are thermal sensor
profiles attributed to Yukon Highways and Public Works / Geological Survey.
There is no exact alias match. These support retaining distinct borehole/site and
method observations, while documenting spatial/campaign dependence. They should
not be described as independent regional replicates or filtered solely for sharing
the CALM campaign years. CALM grid extent or node-level links were not recovered,
so possible borehole-to-grid contextual overlap remains unquantified.

The remaining close stations are the three HPW_Dempster_km421 field/road/toe sites
(776--785 m from NCSS 91FN260007, different coverage years), four YukonU_AH sites
near CALM_C24, and YukonU_OCF_S1_2018_BH1_F near the Moore transects. The latter
YukonU records have no usable annual-summary subsurface values in this screen and
require raw-data availability review. No thermal station is within 2 km of a
Smith/Burgess or Fisher comparison observation. Stewart Crossing has no close
existing comparison point within 2 km; proximity supplies no thermal inference.

No production files, observations or release permissions were changed. Expected
archive location counts, 73 thaw sites, zero 2-km thaw pairs and the 44 close
PF-profile sites with zero same-period pairs are asserted by the geotech script.
