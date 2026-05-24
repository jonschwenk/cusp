# Quality Flags

CUSP uses compact quality flag codes in the main release table so users can
filter caveats without joining a separate observation-level table. The
`quality_flags` column is blank when no current quality flag applies. Multiple
flags are separated with semicolons, for example `LB;DA`.

Quality flags describe caveats and processing choices. They are not a
trustworthy-to-untrustworthy ranking.

## Flag Definitions

The canonical vocabulary lives in `data/quality_flag_definitions.csv`.

| Code | Flag | Category | Definition |
|---|---|---|---|
| `LB` | `lower_bound_absence` | censoring | Permafrost was not reached within the reported probe profile or observation limit. |
| `UB` | `upper_bound_presence` | censoring | Permafrost was confirmed but exact thaw or permafrost depth is only bounded. |
| `OA` | `obs_limit_assumed` | censoring | Observation limit was assigned from protocol source interpretation or processor convention rather than a row-specific measured limit. |
| `PB` | `obs_limit_profile_bottom` | censoring | Permafrost absence is interpreted to the bottom of an observed soil or profile record. |
| `DA` | `date_assigned` | temporal | Date was assigned from year campaign midpoint or representative thaw-season convention. |
| `DS` | `date_source_approximate` | temporal | Source flags the observation date as approximate range-based or otherwise imprecise. |
| `CS` | `coord_site_level` | spatial | Site or event coordinate is repeated for observations that are more spatially granular than the coordinate. |
| `CI` | `coord_lookup_or_interpolated` | spatial | Coordinates were assigned from lookup tables or interpolated along transects. |
| `CF` | `coord_source_flagged` | spatial | Source flags coordinate uncertainty likely coordinate problems or georeferenced coordinates. |
| `SS` | `summary_statistic` | aggregation | Canonical observation value is a mean annual site summary or other source or processor summary statistic. |
| `TI` | `temperature_inferred` | method | Permafrost state or depth was inferred from temperature profile logic. |
| `GI` | `geophysics_inferred` | method | Depth was inferred from GPR ERT or other geophysical interpretation rather than direct probing or coring. |
| `ME` | `model_or_estimate` | derivation | Source or CUSP processor uses modeled estimated extrapolated or reconstructed depth. |
| `FE` | `figure_extracted` | derivation | Value or coordinate was extracted georeferenced or digitized from a figure. |
| `PA` | `pf_state_assumed` | interpretation | Permafrost presence state was assigned from study context threshold logic or source convention rather than explicit row-level presence or absence. |
| `MU` | `method_approximate_or_unknown` | method | Observation method is unknown or mapped approximately into the CUSP method vocabulary. |
| `RC` | `source_unit_or_code_recoded` | source_cleanup | Units sentinels coordinate signs or source codes were recoded to make the row usable. |
| `DO` | `possible_duplicate_or_overlap` | duplication | Known potential overlap with another source remains or source-specific deduplication affected interpretation. |
| `RO` | `refusal_or_obstruction_note` | field_condition | Field notes indicate rock gravel obstruction bottoming out road water or similar ambiguity. |

Source-level quality summaries are described separately in
[Source metadata](source-metadata.md).
