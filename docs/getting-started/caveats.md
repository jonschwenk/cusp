# Caveats

**It is recommended that you read this page *in full* before using CUSP in any
way.**

CUSP brings many source datasets into one shared format. That makes the data
easier to use, but it also means that some source-specific choices have already
been made before the records appear in the release table. Users should treat
CUSP as a carefully documented synthesis, not as a replacement for reading the
source datasets and publications behind the records they use.

## Source Differences

CUSP sources were collected for different projects, at different times, with
different measurement methods. A shared row format cannot remove those
differences. Important variation may remain in:

- field method, such as thaw probing, augering, pits, thaw tubes, temperature
  profiles, geophysics, or remote-sensing-assisted interpretation
- observation season and timing within the thaw season
- whether a record reports direct permafrost presence, thaw depth, active-layer
  thickness, depth to permafrost, or an observation limit
- spatial sampling design, from dense local grids to widely separated field
  sites
- original coordinate precision and site-location reporting

The `method` and `source` columns are meant to help users keep those differences
visible during analysis.

## Interpretation During Processing

Each source has its own processing script. Those scripts convert source files
into the common CUSP schema and may need to make documented interpretation
choices. Common examples include:

- converting depths to centimeters
- converting source-specific permafrost or frost-table labels into
  `pf_observed`
- mapping source methods into the CUSP method vocabulary
- deriving `pf_depth`, `thaw_depth`, or `obs_limit` from source fields
- treating source sentinel values, blanks, or special codes as missing values
- assigning campaign-level or year-level dates when the source does not provide
  exact observation dates
- filtering rows that are duplicate, invalid, outside the source scope, or not
  usable as near-surface permafrost observations

These choices are part of the synthesis. When they matter for your analysis,
check the source-processing script and the original source documentation.

## Presence, Absence, And Observation Limits

`pf_observed = 1` means permafrost was observed in the source workflow.
`pf_observed = 0` means permafrost was not observed within the reported
observation context. It does not always mean that permafrost is absent at all
depths, nearby locations, or later dates.

The `obs_limit` column is especially important for absence-like observations.
It records the depth limit of the observation when available. A shallow
observation with no permafrost encountered should be interpreted differently
from a deeper observation with the same `pf_observed` value.

## Dates And Seasonality

Near-surface permafrost observations are seasonally sensitive. Thaw depth and
active-layer thickness can change substantially within a single summer. CUSP
preserves dates where possible, but some sources only support approximate
dates, campaign dates, or year-level timing. Users should be careful when
combining records from different parts of the thaw season.

## Location And Scale

CUSP uses point coordinates when possible, but coordinate precision varies by
source. Some records may represent a plot, transect, grid cell, field site, or
sampling area rather than a precisely surveyed point. This matters when joining
CUSP to environmental rasters, especially coarse climate, soil, or surface
water layers.

## Dense Sampling

Some CUSP sources contain many observations in a very small area. Those records
are valuable, but they can overweight a local field site in analyses that assume
independent or evenly distributed observations. The
[aggregation guide](../user/aggregation-guide.md) describes one way to create
spatial and temporal summaries when that is more appropriate for your use case.

## Feature Sampling

The feature table, when used, contains environmental variables sampled from
Google Earth Engine. Those features inherit the uncertainty, spatial resolution,
temporal coverage, and processing choices of the source raster products. They
should not be treated as field measurements taken at the CUSP observation site.

For details, see [GEE feature sampling](../user/feature-sampling.md).

## Attribution

Permafrost observations are costly in time and money. If you use CUSP, you are
responsible for citing CUSP and the original datasets or publications behind the
records you used. See [Data use and attribution](../user/data-use-and-attribution.md).
