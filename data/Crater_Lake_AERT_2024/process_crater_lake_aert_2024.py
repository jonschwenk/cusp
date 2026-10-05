"""
metadata_schema_version = 1
source_key = "Crater_Lake_AERT_2024"
release_clearance = "needs_review"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-10-05"
source_dataset = '''
Herring, T., Farzamian, M., Vieira, G., and de Pablo, M. A. (2024).
Automated A-ERT data filtering, inversion, and analysis in permafrost studies:
open-source notebook and data from Deception Island, Antarctica. Zenodo v1.0.
https://doi.org/10.5281/zenodo.13754727
Only data_AERT/probing_data.txt is ingested. Data creators are Farzamian,
Vieira, and de Pablo; Herring created the notebook.
Related paper: Farzamian et al. (2024), https://doi.org/10.5194/tc-18-4197-2024
'''
processing_assumptions = [
  "Retain ten direct manual thaw-probe values: two source-labelled nodes on five exact survey dates. The source notebook divides probe values by 100 to plot metres, establishing input centimetres.",
  "The paper identifies probing of the active layer at a monitored permafrost site. Positive thaw depths imply presence; pf_depth equals thaw_depth. No absence, observation limit, or ERT-derived depth is invented.",
  "Exclude the five mean cells because they summarize the two retained probe values, not additional measurements. Keep their reported values as provenance without recomputing rounded means.",
  "CALM_South A16 contains annual grid summaries for all five survey years. These are not copies of individual node observations; preserve both representations, flag possible_duplicate_or_overlap, and document their statistical dependence. Do not add the two-node means as further summaries.",
]
temporal_handling = [
  "Preserve all five reported ISO survey dates without seasonal placeholders or annual thinning: 2009-02-15, 2010-01-30, 2011-02-10, 2019-02-04, and 2020-02-15.",
]
spatial_handling = [
  "Use only the representative Crater Lake CALM-S site coordinate published in section 2.1: 62 degrees 59 minutes 06.7 seconds S, 60 degrees 40 minutes 44.8 seconds W. Flag coord_site_level on every row; these are not node-specific GPS positions.",
  "Preserve bracket node identifiers [3,2] and [3,3] unchanged. Do not infer their axis order or interpolate positions from the separate 50 cm temperature-sensor GIS archive.",
]
manual_steps = [
  "Extract data_AERT/probing_data.txt unchanged from the Zenodo v1.0 archive teddiherring/AERT-v1.0.zip; input_manifest.json preserves the archive checksum and member path. Preserve the Zenodo record metadata snapshot.",
]
known_limitations = [
  "The two probes share a site coordinate, not a surveyed point location. Retained grid labels do not establish a georeferencing transform. The source grid is 100 m by 100 m.",
  "Individual probe measurements and CALM_South annual grid summaries are different resolutions of the same monitoring programme, not statistically independent samples. Exact CALM annual survey dates and contributing nodes are not supplied by the summary workbook.",
  "Raw resistivity, inverted model cells, threshold-derived thaw interfaces, climate data, and temperature time series are not imported. Deriving further depths requires separate scientific review.",
]
external_dependencies = [
  "pandas and CUSP's data_utils; processing is offline. CALM_South is the documented overlap source, not a required input to reproduce the direct probe measurements.",
]
notes = "Zenodo v1.0 and the related paper are CC BY 4.0. Working ingestion prepared under issue #41; release clearance remains needs_review. No official release export is modified."
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from cusp import data_utils

HERE = Path(__file__).resolve().parent
RAW_SHA256 = "a1758dd1372f5bcb5c198fffa614940f1762058bbd8623492f4e536ead86c947"
NODES = ["[3,2]", "[3,3]"]
SITE_LAT = -(62 + 59 / 60 + 6.7 / 3600)
SITE_LON = -(60 + 40 / 60 + 44.8 / 3600)


def build_processed_table(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if list(raw.columns) != ["date", *NODES, "mean"]:
        raise ValueError("Unexpected probing columns; review the upstream snapshot.")
    if raw.empty or raw["date"].isna().any():
        raise ValueError("Missing survey dates.")
    dates = pd.to_datetime(raw["date"], format="%Y-%m-%d", errors="raise")
    if not dates.dt.strftime("%Y-%m-%d").eq(raw["date"]).all():
        raise ValueError("Survey dates must be exact ISO dates.")
    if raw["date"].duplicated().any():
        raise ValueError("Repeated survey date; review rather than collapsing measurements.")
    values = raw[NODES + ["mean"]].apply(pd.to_numeric, errors="raise")
    if not (values.notna().all().all() and values.gt(0).all().all()):
        raise ValueError("Missing or nonpositive probe values require separate interpretation.")
    if not values.lt(float("inf")).all().all():
        raise ValueError("Probe values must be finite.")

    result = raw.assign(**{column: values[column] for column in values}).melt(
        id_vars=["date", "mean"], value_vars=NODES,
        var_name="source_node_id", value_name="source_probe_depth_cm",
    ).rename(columns={"mean": "source_two_node_mean_cm"})
    result["site_id"] = result["source_node_id"]
    result["calm_site_code"] = "A16"
    result["source"] = "Crater_Lake_AERT_2024"
    result["lat"] = SITE_LAT
    result["lon"] = SITE_LON
    result["method"] = "tp"
    result["pf_observed"] = 1
    result["thaw_depth"] = result["source_probe_depth_cm"]
    result["pf_depth"] = result["thaw_depth"]
    result["obs_limit"] = pd.NA
    result["quality_flag_coord_site_level"] = True
    result["quality_flag_possible_duplicate_or_overlap"] = True
    result = result.sort_values(["date", "source_node_id"], kind="stable").reset_index(drop=True)

    audit = raw.melt(id_vars="date", value_vars=NODES + ["mean"],
                     var_name="source_field", value_name="source_depth_cm")
    audit["decision"] = audit["source_field"].map(
        {NODES[0]: "retained_direct_probe", NODES[1]: "retained_direct_probe", "mean": "excluded_derived_mean"}
    )
    data_utils.check_columns(result)
    return result, audit


def main() -> None:
    path = HERE / "probing_data.txt"
    if hashlib.sha256(path.read_bytes()).hexdigest() != RAW_SHA256:
        raise ValueError("Pinned probing snapshot changed; review before processing.")
    processed, audit = build_processed_table(pd.read_csv(path, sep="\t"))
    if len(processed) != 10 or len(audit) != 15 or audit["decision"].eq("excluded_derived_mean").sum() != 5:
        raise ValueError("Unexpected direct-probe accounting.")
    processed.to_csv(HERE / "processed_crater_lake_aert_2024.csv", index=False)
    audit.to_csv(HERE / "processing_audit.csv", index=False)
    print("Crater_Lake_AERT_2024: 10 direct probes, 2 labelled nodes, 5 exact dates; 5 derived means excluded.")


if __name__ == "__main__":
    main()
