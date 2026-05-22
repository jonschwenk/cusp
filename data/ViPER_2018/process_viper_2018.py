#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "ViPER_2018"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-05-21"

source_dataset = '''
Natali, Susan; Kholodov, Alexander; Loranty, Michael (2016): Thaw depth
and organic layer depth from Alaska borehole sites, 2015, 2017, 2018
(ViPER Project). Arctic Data Center. https://doi.org/10.18739/A22J6848J
'''

processing_assumptions = [
  "Only the thaw-depth transect tables for 2015, 2017, and 2018 are ingested into the canonical CUSP observation table.",
  "Organic-layer-depth tables are excluded because organic-layer depth is not a canonical CUSP permafrost/depth observation.",
  "The source metadata says TD is in meters, but the source values and probe-limit notes show the TD values are centimeters; CUSP therefore treats TD as centimeters.",
  "Thaw depth was measured with a metal thaw probe inserted until resistance from frozen ground, so method is mapped to tp.",
  "Rows with numeric TD and no probe-limit note are retained as permafrost-present observations with thaw_depth and pf_depth set to TD.",
  "Rows whose notes say thaw depth exceeded probe length are retained as lower-bound absence observations with pf_observed = 0, obs_limit set to the stated probe length, and thaw_depth/pf_depth left missing.",
  "Source TD values greater than 200 cm without a probe-limit note are excluded as probable data-entry errors because they are inconsistent with neighboring values and the source probe-limit notes.",
  "Rows with nonnumeric TD, including NA values caused by obstruction or missing measurements, are excluded.",
  "Coordinates are joined from the year-specific coordinate files. When only transect endpoint coordinates are supplied, point coordinates are linearly interpolated by source Location along the transect.",
]

temporal_handling = [
  "Observation dates are read from ViPER_TD_OLD_sample_dates_2015_2017_2018.csv by site and year.",
  "Rows for site-years with source date = NA are excluded if present.",
]

spatial_handling = [
  "Latitude and longitude are read from the year-specific coordinate tables in EPSG:4326.",
  "Positive 2015 longitude values are interpreted as missing west-longitude signs and multiplied by -1, consistent with the dataset bounding box and the 2017/2018 coordinate tables.",
  "Point coordinates are interpolated from bracketing transect coordinates when possible.",
  "Rows with a site-level coordinate and no transect endpoint coordinates use that site-level coordinate for all thaw-depth points at the site/transect.",
]

manual_steps = [
  "Download the Arctic Data Center package for DOI 10.18739/A22J6848J and unpack it into data/ViPER_2018."
]

known_limitations = [
  "Transect interpolation assumes that the source Location field is distance in meters along a straight line between supplied coordinate points.",
  "A local comparison against FireALT/Talucci_2024 found overlapping Bonanza Creek rows; CUSP treats ViPER as the direct source and filters those rows in the Talucci_2024 processor.",
  "Rows using site-level coordinates have repeated coordinates for multiple transect locations.",
]

external_dependencies = [
  "Arctic Data Center DOI: 10.18739/A22J6848J",
  "License: Creative Commons Attribution 4.0 International"
]

notes = ""
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from cusp import data_utils
from cusp.data_utils import _ROOT_DIR


source = "ViPER_2018"
source_dir = _ROOT_DIR / "data" / source
data_dir = source_dir / "data"
output_path = source_dir / f"processed_{source.lower()}.csv"

YEARS = (2015, 2017, 2018)
IMPLAUSIBLE_TD_CM = 200.0


def clean_text(series: pd.Series) -> pd.Series:
    """Strip text values and convert empty strings and NA-like strings to missing."""

    cleaned = series.astype("string").str.strip()
    return cleaned.mask(cleaned.isin(["", "NA", "N/A", "nan"]))


def read_clean_csv(path: Path) -> pd.DataFrame:
    """Read a ViPER CSV and remove blank trailing columns/rows."""

    df = pd.read_csv(path, dtype=str, low_memory=False)
    df = df.rename(columns=lambda value: str(value).strip())
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df = df.replace(r"^\s*$", pd.NA, regex=True)
    df = df.dropna(how="all").copy()
    return df


def read_dates() -> pd.DataFrame:
    """Return site/year observation dates and site names."""

    raw = read_clean_csv(data_dir / "ViPER_TD_OLD_sample_dates_2015_2017_2018.csv")
    raw = raw.rename(columns={"Site Number": "site_number", "Site name": "site_name"})
    raw["site_number"] = pd.to_numeric(raw["site_number"], errors="coerce").astype("Int64")

    records: list[pd.DataFrame] = []
    for year in YEARS:
        column = f"{year} date"
        subset = raw[["site_number", "site_name", column]].copy()
        subset["viper_year"] = year
        subset = subset.rename(columns={column: "source_date"})
        subset["source_date"] = clean_text(subset["source_date"])
        subset["date"] = pd.to_datetime(
            subset["source_date"], format="%m/%d/%y", errors="coerce"
        ).dt.strftime("%Y-%m-%d")
        records.append(subset)

    return pd.concat(records, ignore_index=True)


def read_thaw_depth(year: int) -> pd.DataFrame:
    """Read and normalize a year-specific thaw-depth table."""

    df = read_clean_csv(data_dir / f"ViPER_TD_{year}.csv")
    df = df.rename(
        columns={
            "Site": "site_number",
            "Transect": "transect",
            "Location": "location_m",
            "TD": "viper_td_cm",
            "Notes": "viper_notes",
        }
    )
    df["viper_year"] = year
    df["site_number"] = pd.to_numeric(df["site_number"], errors="coerce").astype("Int64")
    df["transect"] = pd.to_numeric(df["transect"], errors="coerce").astype("Int64")
    df["location_m"] = pd.to_numeric(df["location_m"], errors="coerce")
    df["viper_td_cm"] = pd.to_numeric(df["viper_td_cm"], errors="coerce")
    df["viper_notes"] = clean_text(df.get("viper_notes", pd.Series(pd.NA, index=df.index)))
    return df.dropna(subset=["site_number", "transect", "location_m"]).copy()


def read_coordinates(year: int) -> pd.DataFrame:
    """Read and normalize a year-specific coordinate table."""

    df = read_clean_csv(data_dir / f"ViPER_Coordinates_{year}.csv")
    df = df.rename(
        columns={
            "Site": "site_number",
            "Transect": "transect",
            "Location": "location_m",
            "Lat": "lat",
            "Long": "lon",
        }
    )
    df["viper_year"] = year
    df["site_number"] = pd.to_numeric(df["site_number"], errors="coerce").astype("Int64")
    df["transect"] = pd.to_numeric(df["transect"], errors="coerce").astype("Int64")
    df["location_m"] = pd.to_numeric(df["location_m"], errors="coerce")
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df.loc[df["lon"] > 0, "lon"] = -df.loc[df["lon"] > 0, "lon"]
    return df.dropna(subset=["site_number", "transect", "lat", "lon"]).copy()


def assign_coordinates(thaw: pd.DataFrame, coords: pd.DataFrame) -> pd.DataFrame:
    """Assign exact, interpolated, or site-level coordinates to thaw-depth rows."""

    df = thaw.copy()
    df["lat"] = np.nan
    df["lon"] = np.nan
    df["viper_coordinate_source"] = pd.NA

    for (site_number, transect), group_index in df.groupby(["site_number", "transect"], dropna=False).groups.items():
        group_rows = df.loc[group_index]
        coord_rows = coords.loc[
            coords["site_number"].eq(site_number) & coords["transect"].eq(transect)
        ].copy()
        transect_coords = coord_rows.dropna(subset=["location_m"]).sort_values("location_m")

        if len(transect_coords) >= 2:
            locations = transect_coords["location_m"].to_numpy(dtype=float)
            latitudes = transect_coords["lat"].to_numpy(dtype=float)
            longitudes = transect_coords["lon"].to_numpy(dtype=float)
            in_range = group_rows["location_m"].between(locations.min(), locations.max(), inclusive="both")
            if in_range.any():
                target = group_rows.loc[in_range, "location_m"].to_numpy(dtype=float)
                df.loc[group_rows.loc[in_range].index, "lat"] = np.interp(target, locations, latitudes)
                df.loc[group_rows.loc[in_range].index, "lon"] = np.interp(target, locations, longitudes)
                exact_locations = set(locations.tolist())
                exact = group_rows.loc[in_range, "location_m"].isin(exact_locations)
                df.loc[group_rows.loc[in_range].index, "viper_coordinate_source"] = np.where(
                    exact,
                    "source_coordinate_point",
                    "interpolated_transect",
                )
            continue

        site_point = coord_rows.loc[coord_rows["location_m"].isna()]
        if not site_point.empty:
            first = site_point.iloc[0]
            df.loc[group_index, "lat"] = first["lat"]
            df.loc[group_index, "lon"] = first["lon"]
            df.loc[group_index, "viper_coordinate_source"] = "source_site_point"
            continue

        if len(transect_coords) == 1:
            first = transect_coords.iloc[0]
            df.loc[group_index, "lat"] = first["lat"]
            df.loc[group_index, "lon"] = first["lon"]
            df.loc[group_index, "viper_coordinate_source"] = "single_transect_point"

    return df


def probe_limit_from_note(note: object) -> float:
    """Extract a probe-limit observation depth from ViPER notes."""

    if pd.isna(note):
        return np.nan
    value = str(note).lower()
    if re.search(r"115\s*cm", value):
        return 115.0
    if re.search(r"147\s*cm", value):
        return 147.0
    return np.nan


def format_location(value: float) -> str:
    """Format source Location values for stable synthetic point IDs."""

    if pd.isna(value):
        return "NA"
    return f"{float(value):g}".replace(".", "p")


def build_processed_table() -> tuple[pd.DataFrame, dict[str, int]]:
    """Transform ViPER thaw-depth rows into CUSP processed-source rows."""

    dates = read_dates()
    year_frames: list[pd.DataFrame] = []
    for year in YEARS:
        thaw = read_thaw_depth(year)
        coords = read_coordinates(year)
        year_frames.append(assign_coordinates(thaw, coords))

    df = pd.concat(year_frames, ignore_index=True)
    raw_count = len(df)

    df = df.merge(
        dates[["site_number", "site_name", "viper_year", "date", "source_date"]],
        on=["site_number", "viper_year"],
        how="left",
        validate="many_to_one",
    )

    df["viper_probe_limit_cm"] = df["viper_notes"].map(probe_limit_from_note)
    probe_limit = df["viper_probe_limit_cm"].notna()
    plausible_exact = df["viper_td_cm"].le(IMPLAUSIBLE_TD_CM) | df["viper_td_cm"].isna()
    implausible_unflagged = df["viper_td_cm"].gt(IMPLAUSIBLE_TD_CM) & ~probe_limit

    usable = (
        df["viper_td_cm"].notna()
        & (probe_limit | plausible_exact)
        & ~implausible_unflagged
        & df["date"].notna()
        & df["lat"].notna()
        & df["lon"].notna()
    )
    df = df.loc[usable].copy()

    lower_bound = df["viper_probe_limit_cm"].notna()
    site_numbers = df["site_number"].astype(int).astype(str).str.zfill(2)
    transects = df["transect"].astype(int).astype(str)
    locations = df["location_m"].map(format_location)
    df["site_id"] = (
        "ViPER_"
        + df["viper_year"].astype(str)
        + "_S"
        + site_numbers
        + "_T"
        + transects
        + "_L"
        + locations
    )

    processed = pd.DataFrame(
        {
            "site_id": df["site_id"],
            "source": source,
            "date": df["date"],
            "lat": df["lat"],
            "lon": df["lon"],
            "pf_observed": np.where(lower_bound, 0, 1).astype(int),
            "pf_depth": np.where(lower_bound, np.nan, df["viper_td_cm"]),
            "thaw_depth": np.where(lower_bound, np.nan, df["viper_td_cm"]),
            "obs_limit": np.where(lower_bound, df["viper_probe_limit_cm"], np.nan),
            "method": "tp",
            "viper_year": df["viper_year"],
            "viper_site_number": df["site_number"].astype(int),
            "viper_site_name": df["site_name"],
            "viper_transect": df["transect"].astype(int),
            "viper_location_m": df["location_m"],
            "viper_td_cm": df["viper_td_cm"],
            "viper_probe_limit_cm": df["viper_probe_limit_cm"],
            "viper_notes": df["viper_notes"],
            "viper_source_date": df["source_date"],
            "viper_coordinate_source": df["viper_coordinate_source"],
        }
    )

    stats = {
        "raw_count": int(raw_count),
        "processed_count": int(len(processed)),
        "dropped_count": int(raw_count - len(processed)),
        "dropped_nonnumeric_td": int(df["viper_td_cm"].isna().sum()),
        "implausible_unflagged": int(implausible_unflagged.sum()),
    }
    return (
        processed.sort_values(["site_id", "date"], kind="mergesort").reset_index(drop=True),
        stats,
    )


def main() -> None:
    processed, stats = build_processed_table()

    data_utils.check_columns(processed)
    processed.to_csv(output_path, index=False)

    print(f"Processed {len(processed)} ViPER_2018 observations.")
    print(f"Dropped {stats['dropped_count']} rows without usable TD, date, coordinates, or plausible values.")
    print(f"Unflagged TD values above {IMPLAUSIBLE_TD_CM:g} cm in raw tables: {stats['implausible_unflagged']}.")
    print("pf_observed counts:")
    print(processed["pf_observed"].value_counts(dropna=False).sort_index().to_string())
    print("Coordinate source counts:")
    print(processed["viper_coordinate_source"].value_counts(dropna=False).sort_index().to_string())


if __name__ == "__main__":
    main()
