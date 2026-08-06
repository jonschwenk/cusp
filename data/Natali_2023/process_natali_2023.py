#!/usr/bin/env python3
"""
metadata_schema_version = 1
source_key = "Natali_2023"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-06"
source_dataset = '''
Natali, S.; Ludwig, S.; Minions, C.; Watts, J. D. 2023. ABoVE: Thaw Depth at
Selected Unburned and Burned Sites Across Alaska (Version 1.0). ORNL
Distributed Active Archive Center. https://doi.org/10.3334/ORNLDAAC/1579
'''
processing_assumptions = [
  "Ordinary numeric thaw depths are direct probe detections and are retained as permafrost presence; no arbitrary depth threshold is used.",
  "Notes stating that thaw exceeded the 109, 115, or 147 cm probe length are retained as lower-bound absence observations with the stated row-specific obs_limit.",
  "One source value of 552 cm at NCU_OLD on 2017-09-18 is corrected to 52 cm because the same observation is 52 cm in FireALT and 552 cm is incompatible with neighboring 34-63 cm values.",
  "Rows with missing thaw depth caused by rock or with no usable lower-bound note are excluded.",
  "The 93 EML observations from 2017-09-20 are removed because the earlier ViPER_2018 release contains the same transects; ViPER is retained as the primary source.",
  "method is set to tp for all retained rows.",
]
temporal_handling = [
  "Per-record dates are stripped and parsed directly from the source CSV.",
]
spatial_handling = [
  "Each site/date/transect has coordinates at its two endpoints; coordinates for interior sample_location values are linearly interpolated between those endpoints.",
  "Endpoint rows retain their source coordinates and interior rows carry the coord_lookup_or_interpolated quality flag.",
]
manual_steps = []
known_limitations = [
  "Straight-line interpolation assumes sample_location is distance along the segment joining the two source endpoints.",
  "Numeric rows whose notes report rock are retained but carry refusal_or_obstruction_note because refusal may not represent frozen ground.",
  "The ViPER overlap filter and the 552-to-52 correction are guarded by expected counts so source revisions cannot silently change either decision.",
]
external_dependencies = []
notes = ""
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from cusp import data_utils
from cusp.data_utils import _ROOT_DIR


SOURCE = "Natali_2023"
INPUT_PATH = _ROOT_DIR / "data" / SOURCE / "thaw_depth.csv"
OUTPUT_PATH = _ROOT_DIR / "data" / SOURCE / f"processed_{SOURCE.lower()}.csv"
EXPECTED_RAW_ROWS = 3_028
EXPECTED_GROUPS = 98
EXPECTED_VIPER_COPIES = 93
EXPECTED_RECODED_VALUES = 1


def probe_limit_from_note(note: object) -> float:
    """Return an explicit probe-length lower bound recorded in a source note."""

    if pd.isna(note):
        return np.nan
    text = str(note).strip().lower()
    for limit in (109.0, 115.0, 147.0):
        if re.search(rf"\b{int(limit)}\b", text):
            return limit
    return np.nan


def interpolate_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """Interpolate interior point coordinates from each transect's endpoints."""

    result = df.copy()
    result["natali_coordinate_source"] = pd.NA
    groups = result.groupby(["site_code", "date", "transect"], dropna=False)
    if groups.ngroups != EXPECTED_GROUPS:
        raise ValueError(
            f"Expected {EXPECTED_GROUPS} Natali transects; found {groups.ngroups}."
        )

    for group_key, indexes in groups.groups.items():
        rows = result.loc[indexes]
        endpoints = rows.dropna(subset=["lat", "lon"]).sort_values("sample_location")
        if len(endpoints) != 2:
            raise ValueError(
                f"Expected two coordinate endpoints for {group_key}; found {len(endpoints)}."
            )
        endpoint_locations = endpoints["sample_location"].to_numpy(dtype=float)
        targets = rows["sample_location"].to_numpy(dtype=float)
        if targets.min() < endpoint_locations.min() or targets.max() > endpoint_locations.max():
            raise ValueError(f"Transect observations fall outside endpoints for {group_key}.")

        result.loc[indexes, "lat"] = np.interp(
            targets, endpoint_locations, endpoints["lat"].to_numpy(dtype=float)
        )
        result.loc[indexes, "lon"] = np.interp(
            targets, endpoint_locations, endpoints["lon"].to_numpy(dtype=float)
        )
        result.loc[indexes, "natali_coordinate_source"] = np.where(
            rows["sample_location"].isin(endpoint_locations),
            "source_endpoint",
            "interpolated_transect",
        )
    return result


def main() -> None:
    df = pd.read_csv(INPUT_PATH)
    if len(df) != EXPECTED_RAW_ROWS:
        raise ValueError(f"Expected {EXPECTED_RAW_ROWS} raw Natali rows; found {len(df)}.")

    df = df.rename(
        columns={"latitude ": "lat", "longitude ": "lon", "notes ": "natali_notes"}
    )
    for column in ("site_name", "site_code", "date", "natali_notes"):
        df[column] = df[column].astype("string").str.strip()
    for column in ("lat", "lon", "transect", "sample_location", "thaw_depth"):
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df[["lat", "lon", "thaw_depth"]] = df[["lat", "lon", "thaw_depth"]].replace(
        -9999, np.nan
    )
    df["date"] = pd.to_datetime(df["date"], errors="raise").dt.strftime("%Y-%m-%d")
    df = interpolate_coordinates(df)

    source_thaw_depth = df["thaw_depth"].copy()
    recoded_value = df["thaw_depth"].eq(552)
    if int(recoded_value.sum()) != EXPECTED_RECODED_VALUES:
        raise ValueError(
            "Expected one Natali 552 cm source typo; "
            f"found {int(recoded_value.sum())}."
        )
    df.loc[recoded_value, "thaw_depth"] = 52.0

    df["natali_probe_limit_cm"] = df["natali_notes"].map(probe_limit_from_note)
    lower_bound = df["natali_probe_limit_cm"].notna()
    usable = df["thaw_depth"].notna() | lower_bound
    df = df.loc[usable].copy()
    lower_bound = lower_bound.loc[df.index]

    viper_copy = df["site_code"].eq("EML") & df["date"].eq("2017-09-20")
    if int(viper_copy.sum()) != EXPECTED_VIPER_COPIES:
        raise ValueError(
            f"Expected {EXPECTED_VIPER_COPIES} Natali/ViPER copies; "
            f"found {int(viper_copy.sum())}."
        )
    df = df.loc[~viper_copy].copy()
    lower_bound = lower_bound.loc[df.index]

    transect = df["transect"].astype("Int64").astype("string")
    location = df["sample_location"].map(lambda value: f"{float(value):g}")
    output = pd.DataFrame(
        {
            "site_id": SOURCE + "_" + df["site_code"] + "_T" + transect + "_L" + location,
            "date": df["date"],
            "lat": df["lat"],
            "lon": df["lon"],
            "thaw_depth": df["thaw_depth"].where(~lower_bound),
            "pf_observed": np.where(lower_bound, 0, 1).astype(int),
            "pf_depth": df["thaw_depth"].where(~lower_bound),
            "obs_limit": df["natali_probe_limit_cm"].where(lower_bound),
            "method": "tp",
            "source": SOURCE,
            "site_name": df["site_name"],
            "transect_name": transect,
            "transect_point": df["sample_location"],
            "natali_source_thaw_depth_cm": source_thaw_depth.loc[df.index],
            "natali_notes": df["natali_notes"],
            "natali_coordinate_source": df["natali_coordinate_source"],
            "quality_flag_coord_lookup_or_interpolated": df[
                "natali_coordinate_source"
            ].eq("interpolated_transect"),
            "quality_flag_source_unit_or_code_recoded": recoded_value.loc[df.index],
            "quality_flag_refusal_or_obstruction_note": (
                df["natali_notes"].str.contains("rock", case=False, na=False)
                & ~lower_bound
            ),
        }
    )

    data_utils.check_columns(output)
    output.to_csv(OUTPUT_PATH, index=False)
    print(
        f"Removed {EXPECTED_VIPER_COPIES} ViPER copies; wrote {len(output):,} "
        f"Natali observations ({int(lower_bound.sum())} lower-bound absences)."
    )


if __name__ == "__main__":
    main()
