# Caveats

**Please read this page in full before using CUSP.**

CUSP combines observations from many datasets in one shared table. This makes
the data easier to find and compare, but it does not make all measurements
equivalent. Some source-specific interpretation and conversion are needed
before a record can fit the common CUSP columns. Treat CUSP as a documented
synthesis, and consult the original datasets and publications when their
methods or limitations matter to your study.

## Source Differences

Each source dataset was collected for its own research purpose, at a particular
time, and with particular field methods. Important differences remain in:

- field method, such as thaw probing, augering, pits, thaw tubes, temperature
  profiles, geophysics, or remote-sensing-assisted interpretation
- observation season and timing within the thaw season
- what was reported, such as permafrost presence, thaw depth, active-layer
  thickness, depth to permafrost, or the deepest depth examined
- spatial sampling design, from dense local grids to widely separated field
  sites
- original coordinate precision and site-location reporting

Use the `method` and `source` columns to keep these differences visible during
analysis. A row from one method should not automatically be treated as
interchangeable with a row from another.

## Quality Flags

The main release table includes `quality_flags`, a semicolon-delimited list of
short codes that call attention to known caveats or processing choices. For
example, `LB;DA` means that permafrost was not reached within the reported
observation depth and that CUSP assigned a representative date. A blank value
means that no current flag applies; it does not mean that the measurement is
exact or free of uncertainty.

See the [quality flag definitions](../user/quality-flags.md#flag-definitions)
for the meaning of every code. Consult those definitions before excluding
specific caveats such as coordinate source flags, geophysics-inferred
observations, or lower-bound absence observations. A flag records a caveat or
processing choice; it is not by itself a reason to discard a row.

## How Source Data Become CUSP Rows

Each source has processing code that translates its original fields into the
common CUSP columns. Depending on the source, this may involve:

- converting depths to centimeters
- translating source-specific permafrost or frost-table labels into the CUSP
  presence field, `pf_observed`
- mapping source methods into the CUSP method vocabulary
- deriving `pf_depth`, `thaw_depth`, or `obs_limit` from source fields
- recognizing source-specific missing-value codes, blanks, or special values
- assigning campaign-level or year-level dates when the source does not provide
  exact observation dates
- removing duplicate or invalid rows and records outside CUSP's scope

These decisions are documented in the source-processing code and metadata.
Check those records and the original source documentation when a particular
measurement, flag, or conversion matters to your analysis.

## Presence, Absence, And Observation Limits

`pf_observed` is a simple summary of what the original record reported:

- `pf_observed = 1` means that the source reported permafrost at that location
  and time.
- `pf_observed = 0` means that the source did not find permafrost within the
  depth or observation represented by the row. It does not mean that
  permafrost is absent at every depth, at nearby locations, or at later dates.

For a probe, pit, core, temperature profile, or similar below-ground
measurement that did not reach permafrost, `obs_limit` records the deepest
depth supported by the observation. For example, a row with
`pf_observed = 0` and `obs_limit = 120` means that permafrost was not detected
in the upper 120 cm. It makes no claim below 120 cm. `pf_depth` and
`thaw_depth` are blank on these no-detection rows.

Some sources provide visual or mapped presence/absence classifications rather
than a below-ground measurement at one point. These rows carry the `VI` flag
and may have no `obs_limit`. Treat them as qualitative classifications, and
exclude `VI` rows when an analysis requires a measured search depth.

When a source reports a numeric thaw depth or depth to permafrost, CUSP treats
that record as a detection. CUSP creates a no-detection row only when the source
explicitly reports that permafrost was not found and provides enough
information to describe the observation limit, apart from the flagged visual
case above. `LB` marks lower-bound no-detections; `OA` and `PB` indicate whether
the limit was assigned from documented context or taken from the bottom of a
measured profile.

## Dates And Seasonality

Thaw depth and active-layer thickness can change substantially during a single
summer. CUSP preserves exact dates when the source provides them, but some
records have only an approximate date, a campaign date, or a year. Check date
flags and avoid treating observations from different parts of the thaw season
as directly comparable without considering that timing.

## Location And Scale

CUSP uses point coordinates when possible, but coordinate precision varies.
A coordinate may identify a precise measurement point or may stand for a plot,
transect, grid cell, field site, or larger sampling area. Review spatial quality
flags before making fine-scale map comparisons or sampling environmental
rasters at a CUSP coordinate.

## Dense Sampling

Some sources contain many closely spaced measurements from one field site.
Those observations are valuable, but they can give that site disproportionate
influence in an analysis that treats every row as independent.

For dense ground-penetrating radar (GPR) surveys, CUSP normally summarizes
native measurements as one mean row per occupied 5 m by 5 m grid cell for each
source, site, and observation date. Measurements from different dates or thaw
years remain separate. The supporting tables retain the number of native
measurements and the aggregation spacing, so a summarized 5 m row should not
be interpreted as one original instrument reading. A source may use a
documented exception when its survey design requires one.

Duplicate handling also depends on source documentation. When a later
synthesis republishes an identifiable original dataset, CUSP keeps the
original source and removes the copied records from the later synthesis.
Records are not removed merely because their coordinates overlap, especially
when they represent different dates or thaw years.

The [aggregation guide](../user/aggregation-guide.md) describes one way to create
spatial and temporal summaries when that is more appropriate for your use case.

## Feature Sampling

Optional feature tables contain environmental values sampled from Google Earth
Engine products. These values inherit the uncertainty, spatial resolution,
time coverage, and processing choices of the original raster products. They
are contextual data, not field measurements collected with the CUSP
observation.

For details, see [GEE feature sampling](../user/feature-sampling.md).

## Attribution

Scientific publications using CUSP are expected to cite CUSP and every
original dataset or publication represented in the rows used. See
[Attribution and BibTeX](../user/data-use-and-attribution.md) for the required
workflow and citation helper.
