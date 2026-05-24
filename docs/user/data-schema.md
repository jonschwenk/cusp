# CUSP Data Schema

This document describes the stable public columns in the main CUSP release
table.

The versioned release file is named like `cusp_v1.0.csv`,
`cusp_v1.1.csv`, or `cusp_v2.0.csv`.

For naming and export layout, see
[Versioning and exports](../release/versioning-and-exports.md).

## Canonical observation table

The schema-defining release file is:

- `cusp_vX.Y.csv`

### Column definitions

| Column | Meaning | Type / format | Nulls allowed |
|---|---|---|---|
| `cusp_obs_id` | Stable opaque CUSP observation identifier | string | no |
| `source` | Canonical CUSP source key | string | no |
| `site_id` | Source-provided site or point identifier | string | yes |
| `lat` | Latitude in WGS84 | decimal degrees | no |
| `lon` | Longitude in WGS84 | decimal degrees | no |
| `date` | Observation date | `YYYY-MM-DD` | no |
| `pf_observed` | Permafrost presence indicator | `0` or `1` | no |
| `thaw_depth` | Thaw depth below ground surface | centimeters | yes |
| `pf_depth` | Depth to permafrost below ground surface | centimeters | yes |
| `obs_limit` | Observation limit below ground surface | centimeters | yes |
| `method` | Observation tool code | controlled vocabulary | no |
| `quality_flags` | Semicolon-delimited quality flag codes | string | yes |

### Notes

- `site_id` is warning-only if missing. Some sources do not provide a site ID.
- `pf_observed = 1` means permafrost was observed in the source workflow.
- `pf_observed = 0` means permafrost was not observed within the source
  observation context.
- Numeric nulls mean not reported, not measured, or not inferable from the
  source workflow.
- `thaw_depth`, `pf_depth`, and `obs_limit` are all recorded in centimeters
  below ground surface.
- `quality_flags` is blank when no current quality flag applies.

### Quality flags

The `quality_flags` column contains semicolon-delimited mnemonic codes such as
`LB`, `DA`, or `TI;SS`. Code definitions are maintained in:

- `data/quality_flag_definitions.csv`

Each definition includes the full flag name, compact code, category, and
description. The flags describe caveats, not a trustworthy-to-untrustworthy
ranking. See [Quality flags](quality-flags.md) for the full vocabulary and
[Source metadata](source-metadata.md) for source-level quality summaries.

| Example code | Meaning |
|---|---|
| `LB` | Lower-bound absence: permafrost was not reached within the observation limit. |
| `DA` | Date was assigned from year, campaign, midpoint, or representative thaw-season convention. |
| `TI` | Permafrost state or depth was inferred from temperature profile logic. |
| `GI` | Depth was inferred from geophysical interpretation. |

### Controlled vocabulary for `method`

The method column uses short codes:

| Method | Meaning |
| --- | --- |
| `aug` | auger observation |
| `gp` | ground probing or frost probing where the source uses that terminology |
| `pit` | soil pit or excavation |
| `pit_aug` | combined pit and auger information |
| `temp` | temperature profile or temperature-based interpretation |
| `tp` | thaw probing or frost-table probing |
| `tp_pit` | combined thaw-probe and pit information |
| `tt` | thaw tube |
| `unknown` | observation method was not recoverable from the source |
| `mixed` | aggregated row contains multiple methods; not used in the main observation table |

The main released CUSP table should only contain single-observation method
values, not `mixed`.

Remote-sensing and modeled products that infer active layer or permafrost
conditions from surface displacement, gridded products, or other indirect
products are outside the canonical observation-table method vocabulary.

## Aggregation outputs

The repository includes an aggregation tool that can create spatial and
temporal summaries of CUSP observations. The default output name is:

- `aggregated_30m.csv`

### Aggregated column notes

| Column | Meaning | Type / format |
|---|---|---|
| `cusp_30m_id` | Stable opaque aggregated identifier | string |
| `year` | Calendar year of the grouped observations | integer |
| `date` | Representative grouped date | `YYYY-MM-DD` |
| `lat`, `lon` | Aggregated output coordinates in WGS84 | decimal degrees |
| `pf_observed` | Mean of grouped `0/1` observations | numeric fraction from `0` to `1` |
| `thaw_depth`, `pf_depth` | Median grouped depth values | centimeters |
| `obs_limit` | Maximum grouped observation limit | centimeters |
| `method` | Grouped method label | controlled vocabulary; may be `mixed` |
| `quality_flags` | Union of grouped quality flag codes | string |
| `aggregated_sources` | Semicolon-delimited contributing source keys | string |
| `n_grouped` | Number of grouped observation rows | integer |

### Aggregation behavior

- grouping is computed in projected `EPSG:3413`
- outputs are exported in `EPSG:4326`
- grouping preserves annual separation
- grouping is allowed across sources
- temporal linkage uses a symmetric `31` days backward / `31` days forward rule

## Aggregation sidecars

An aggregation run may also create:

- `aggregated_30m_membership.csv`
- `aggregated_30m_qc_flags.csv`
- `aggregated_30m_excluded_rows.csv`
- `aggregated_30m.gpkg`
- `aggregated_30m_manifest.json`

These are important provenance and QA artifacts. CUSP does not currently
publish an official aggregated release table; it provides the workflow so users
can create summaries that fit their own analysis.

## Keep in mind

- use `cusp_vX.Y.csv` as the stable observation-level table
- use the aggregation workflow when you need a spatial or temporal summary
- use the release bibliography and citation tool to connect `source` values
  back to the underlying sources
