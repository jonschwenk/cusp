#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "PERMOS_2024"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk"
last_substantive_update = "2026-05-21"

source_dataset = '''
PERMOS 2024: PERMOS Database. Swiss Permafrost Monitoring Network,
Davos and Fribourg, Switzerland. https://doi.org/10.13093/permos-2024-01
'''

processing_assumptions = [
  "Only the annual active-layer-thickness table alt_20240529.csv is ingested into the canonical CUSP observation table.",
  "Ground-surface-temperature, ERT, and terrestrial geodetic-survey tables are excluded because they are related monitoring products rather than direct thaw-depth/permafrost-depth observations in the current CUSP schema.",
  "PERMOS ALT is calculated from borehole thermistor temperatures by linear interpolation between neighbouring sensors above and below the permafrost table; CUSP records these rows with method = temp.",
  "ALT values are converted from meters to centimeters.",
  "Rows with a numeric ALT and date are retained.",
  "Rows with ALT < x m comments are retained as permafrost-present upper-bound observations: pf_observed = 1, obs_limit is set to x, and exact thaw_depth/pf_depth are left missing.",
  "Rows with ALT between x and y m comments are retained as lower-bound absence observations: pf_observed = 0, obs_limit is set to x, and exact thaw_depth/pf_depth are left missing.",
  "Exact ALT rows already represented in CALM are filtered out by matching PERMOS calm_id, PERMOS year, and reported ALT depth against data/CALM/processed_calm.csv.",
  "Bounded or otherwise nonexact ALT rows with CALM identifiers are filtered out when CALM already represents the same calm_id and year.",
  "Retained rows whose comments state ALT > a reported depth are treated as lower-bound observations where permafrost was not observed within the reported limit: pf_observed = 0, obs_limit is set to the reported ALT value, and thaw_depth/pf_depth are left missing.",
  "All other retained numeric ALT rows are treated as permafrost-present observations with thaw_depth and pf_depth equal to the reported ALT.",
  "PERMOS guess flags and ALT comments are retained as provenance fields and are not used to filter numeric ALT rows.",
]

temporal_handling = [
  "The PERMOS date field is the date of maximum ALT and is written directly as the CUSP observation date.",
  "Bound-only rows without a PERMOS date are assigned September 1 of the PERMOS year, following the CUSP convention for Northern Hemisphere year-only thaw-season observations.",
  "The PERMOS year field is retained separately as provenance because one annual ALT row can have a max-ALT date outside the calendar year.",
]

spatial_handling = [
  "Borehole latitude/longitude are used when available.",
  "If borehole coordinates are missing, site-level latitude/longitude are used as a fallback and the coordinate source is recorded.",
]

manual_steps = [
  "Download PERMOS Database release 2024 from the DOI landing page and unpack the ASCII tables into data/PERMOS_2024/Data."
]

known_limitations = [
  "The ingest excludes no-data, incomplete/not-yet-available, erroneous/unreliable, and talik/no-freeze-through rows from the ALT table.",
  "Talik/no-freeze-through rows are not encoded as absence observations because the source does not provide a usable observation limit.",
  "The CALM overlap filtering is source-specific because the CUSP CALM processor uses year-only dates while PERMOS reports exact maximum-ALT dates.",
  "Eighteen retained rows use site-level coordinates because borehole coordinates are absent in borehole_20240529.csv.",
  "Rows flagged as PERMOS guesses are included but flagged in permos_guess.",
  "PERMOS ALT is derived from in situ thermistor data rather than direct manual probing.",
]

external_dependencies = [
  "data/CALM/processed_calm.csv is required for source-specific overlap filtering.",
  "PERMOS DOI: 10.13093/permos-2024-01",
  "PERMOS Data Policy: CC BY 4.0 with required citation.",
]

notes = ""
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from cusp import data_utils
from cusp.data_utils import _ROOT_DIR


source = "PERMOS_2024"
source_dir = _ROOT_DIR / "data" / source
data_dir = source_dir / "Data"
alt_path = data_dir / "alt_20240529.csv"
borehole_path = data_dir / "borehole_20240529.csv"
site_path = data_dir / "site_20240529.csv"
output_path = source_dir / f"processed_{source.lower()}.csv"
calm_path = _ROOT_DIR / "data" / "CALM" / "processed_calm.csv"


def clean_text(series: pd.Series) -> pd.Series:
    """Strip strings and normalize empty values."""

    cleaned = series.astype("string").str.strip()
    return cleaned.mask(cleaned == "")


def clean_bool(series: pd.Series) -> pd.Series:
    """Normalize PERMOS boolean-like flags to lowercase strings."""

    return clean_text(series).str.lower()


def read_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Read PERMOS ALT, borehole, and site tables."""

    alt = pd.read_csv(alt_path, low_memory=False)
    boreholes = pd.read_csv(borehole_path, low_memory=False)
    sites = pd.read_csv(site_path, low_memory=False)
    return alt, boreholes, sites


def calm_coverage_keys() -> tuple[set[tuple[str, int, float]], set[tuple[str, int]]]:
    """Return CALM coverage keys already represented in CUSP."""

    if not calm_path.exists():
        raise FileNotFoundError(
            f"{calm_path} is required for PERMOS_2024 CALM-overlap filtering."
        )

    calm = pd.read_csv(calm_path, usecols=["site_id", "date", "thaw_depth"], low_memory=False)
    calm["calm_id"] = clean_text(calm["site_id"]).str.replace(r"^CALM_", "", regex=True)
    calm["year"] = pd.to_datetime(calm["date"], errors="coerce").dt.year
    calm["depth_cm"] = pd.to_numeric(calm["thaw_depth"], errors="coerce").round(6)
    calm_years = calm.dropna(subset=["calm_id", "year"])
    calm_depths = calm.dropna(subset=["calm_id", "year", "depth_cm"])

    exact_depth_keys = set(
        zip(
            calm_depths["calm_id"].astype(str),
            calm_depths["year"].astype(int),
            calm_depths["depth_cm"].astype(float),
            strict=False,
        )
    )
    year_keys = set(
        zip(
            calm_years["calm_id"].astype(str),
            calm_years["year"].astype(int),
            strict=False,
        )
    )
    return exact_depth_keys, year_keys


def build_processed_table(
    alt: pd.DataFrame,
    boreholes: pd.DataFrame,
    sites: pd.DataFrame,
) -> pd.DataFrame:
    """Join PERMOS annual ALT to location metadata and return CUSP rows."""

    df = alt.merge(
        boreholes.add_prefix("borehole_"),
        left_on="borehole_id",
        right_on="borehole_id",
        how="left",
        validate="many_to_one",
    )
    df = df.merge(
        sites.add_prefix("site_"),
        left_on="borehole_site_id",
        right_on="site_id",
        how="left",
        validate="many_to_one",
    )

    df["alt_cm"] = pd.to_numeric(df["alt"], errors="coerce") * 100.0
    df["date_parsed"] = pd.to_datetime(df["date"], errors="coerce")
    df["year_int"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["comment_clean"] = clean_text(df["comment"])
    df["lat"] = pd.to_numeric(df["borehole_lat"], errors="coerce").combine_first(
        pd.to_numeric(df["site_lat"], errors="coerce")
    )
    df["lon"] = pd.to_numeric(df["borehole_lon"], errors="coerce").combine_first(
        pd.to_numeric(df["site_lon"], errors="coerce")
    )
    df["coordinate_source"] = np.select(
        [
            df["borehole_lat"].notna() & df["borehole_lon"].notna(),
            df["site_lat"].notna() & df["site_lon"].notna(),
        ],
        ["borehole", "site"],
        default="missing",
    )

    upper_bound_m = df["comment_clean"].str.extract(
        r"(?i)ALT\s*<\s*([0-9]+(?:\.[0-9]+)?)\s*m?"
    )[0].astype(float)
    between_bounds = df["comment_clean"].str.extract(
        r"(?i)ALT\s+between\s+([0-9]+(?:\.[0-9]+)?)\s+and\s+([0-9]+(?:\.[0-9]+)?)\s*m?"
    )
    between_lower_m = between_bounds[0].astype(float)
    greater_bound_m = df["comment_clean"].str.extract(
        r"(?i)ALT\s*>\s*([0-9]+(?:\.[0-9]+)?)\s*m?"
    )[0].astype(float)

    exact_alt = df["alt_cm"].notna() & df["date_parsed"].notna()
    upper_bound_presence = df["alt_cm"].isna() & upper_bound_m.notna()
    between_bound_absence = df["alt_cm"].isna() & between_lower_m.notna()
    greater_bound_absence = greater_bound_m.notna()

    df["permos_bound_type"] = "exact"
    df.loc[upper_bound_presence, "permos_bound_type"] = "upper"
    df.loc[between_bound_absence | greater_bound_absence, "permos_bound_type"] = "lower"

    df["bound_cm"] = np.nan
    df.loc[upper_bound_presence, "bound_cm"] = upper_bound_m.loc[upper_bound_presence] * 100.0
    df.loc[between_bound_absence, "bound_cm"] = between_lower_m.loc[between_bound_absence] * 100.0
    df.loc[greater_bound_absence, "bound_cm"] = df.loc[greater_bound_absence, "alt_cm"].fillna(
        greater_bound_m.loc[greater_bound_absence] * 100.0
    )

    candidate = (
        exact_alt
        | upper_bound_presence
        | between_bound_absence
        | greater_bound_absence
    )
    df["date_source"] = "reported_max_alt_date"
    year_only = candidate & df["date_parsed"].isna() & df["year_int"].notna()
    df.loc[year_only, "date_parsed"] = pd.to_datetime(
        df.loc[year_only, "year_int"].astype(str) + "-09-01",
        errors="coerce",
    )
    df.loc[year_only, "date_source"] = "year_only_september_1"

    df = df.loc[candidate].dropna(subset=["date_parsed", "lat", "lon"]).copy()

    df["calm_overlap_key"] = list(
        zip(
            clean_text(df["borehole_calm_id"]).astype(str),
            df["year_int"],
            df["alt_cm"].round(6),
            strict=False,
        )
    )
    df["calm_year_key"] = list(
        zip(
            clean_text(df["borehole_calm_id"]).astype(str),
            df["year_int"],
            strict=False,
        )
    )
    calm_exact_keys, calm_year_keys = calm_coverage_keys()
    df["covered_by_calm"] = df["calm_overlap_key"].map(
        lambda key: key[0] != "<NA>" and not pd.isna(key[1]) and key in calm_exact_keys
    )
    bound_or_nonexact = df["permos_bound_type"].ne("exact")
    df.loc[bound_or_nonexact, "covered_by_calm"] = df.loc[bound_or_nonexact, "calm_year_key"].map(
        lambda key: key[0] != "<NA>" and not pd.isna(key[1]) and key in calm_year_keys
    )
    df = df.loc[~df["covered_by_calm"]].copy()

    lower_bound = df["permos_bound_type"].eq("lower")
    upper_bound = df["permos_bound_type"].eq("upper")

    borehole_name = clean_text(df["borehole_name"])
    fallback_site_id = "PERMOS_BH_" + df["borehole_id"].astype("string")
    site_id = borehole_name.fillna(fallback_site_id)

    processed = pd.DataFrame(
        {
            "site_id": site_id,
            "source": source,
            "date": df["date_parsed"].dt.strftime("%Y-%m-%d"),
            "lat": df["lat"],
            "lon": df["lon"],
            "pf_observed": np.where(lower_bound, 0, 1).astype(int),
            "pf_depth": np.where(lower_bound | upper_bound, np.nan, df["alt_cm"]),
            "thaw_depth": np.where(lower_bound | upper_bound, np.nan, df["alt_cm"]),
            "obs_limit": np.where(lower_bound | upper_bound, df["bound_cm"], np.nan),
            "method": "temp",
            "permos_alt_id": df["id"],
            "permos_borehole_id": df["borehole_id"],
            "permos_borehole_name": borehole_name,
            "permos_borehole_alternate_name": clean_text(df["borehole_alter_name"]),
            "permos_site_abbr": clean_text(df["site_abbr"]),
            "permos_site_name": clean_text(df["site_name"]),
            "permos_region": clean_text(df["site_region"]),
            "permos_canton": clean_text(df["site_canton"]),
            "permos_year": pd.to_numeric(df["year"], errors="coerce").astype("Int64"),
            "permos_alt_m": pd.to_numeric(df["alt"], errors="coerce"),
            "permos_bound_type": df["permos_bound_type"],
            "permos_bound_cm": df["bound_cm"],
            "permos_date_source": df["date_source"],
            "permos_guess": clean_bool(df["guess"]),
            "permos_upper_therm_m": pd.to_numeric(df["upper_therm"], errors="coerce"),
            "permos_lower_therm_m": pd.to_numeric(df["lower_therm"], errors="coerce"),
            "permos_alt_comment": clean_text(df["comment"]),
            "permos_coordinate_source": df["coordinate_source"],
            "permos_borehole_elevation_m": pd.to_numeric(df["borehole_h"], errors="coerce"),
            "permos_site_elevation_min_m": pd.to_numeric(df["site_h_min"], errors="coerce"),
            "permos_site_elevation_max_m": pd.to_numeric(df["site_h_max"], errors="coerce"),
            "permos_borehole_depth_m": pd.to_numeric(df["borehole_depth"], errors="coerce"),
            "permos_borehole_inclination_deg": pd.to_numeric(df["borehole_inc"], errors="coerce"),
            "permos_borehole_slope_deg": pd.to_numeric(df["borehole_slp"], errors="coerce"),
            "permos_borehole_aspect_deg": pd.to_numeric(df["borehole_asp"], errors="coerce"),
            "permos_morphology": clean_text(df["borehole_morphology"]),
            "permos_surface_type": clean_text(df["borehole_surf_type"]),
            "permos_pf_thickness": clean_text(df["borehole_pf_thick"]),
            "permos_borehole_class": clean_text(df["borehole_class"]),
            "permos_gtnp_id": clean_text(df["borehole_gtnp_id"]),
            "permos_gtnp_dms_id": clean_text(df["borehole_gtnp_dms_id"].astype("string")),
            "permos_calm_id": clean_text(df["borehole_calm_id"]),
            "permos_borehole_comment": clean_text(df["borehole_comment"]),
            "permos_site_comment": clean_text(df["site_comment"]),
        }
    )

    return processed.sort_values(["site_id", "date"], kind="mergesort").reset_index(drop=True)


def main() -> None:
    alt, boreholes, sites = read_tables()
    numeric_date_candidate = pd.to_numeric(alt["alt"], errors="coerce").notna() & pd.to_datetime(
        alt["date"], errors="coerce"
    ).notna()
    comment = clean_text(alt["comment"])
    bound_candidate = comment.str.contains(
        r"(?i)ALT\s*<\s*[0-9]|ALT\s+between\s+[0-9]|ALT\s*>\s*[0-9]",
        regex=True,
        na=False,
    )
    n_candidate = int((numeric_date_candidate | bound_candidate).sum())
    processed = build_processed_table(alt, boreholes, sites)

    data_utils.check_columns(processed)
    processed.to_csv(output_path, index=False)

    print(f"Processed {len(processed)} PERMOS_2024 ALT observations from {alt_path.name}.")
    print(f"Dropped {len(alt) - n_candidate} ALT rows without usable numeric or bounded ALT information.")
    print(f"Filtered {n_candidate - len(processed)} ALT rows already represented in CALM.")
    print("Method counts:")
    print(processed["method"].value_counts(dropna=False).sort_index().to_string())
    print("pf_observed counts:")
    print(processed["pf_observed"].value_counts(dropna=False).sort_index().to_string())
    print("Coordinate source counts:")
    print(processed["permos_coordinate_source"].value_counts(dropna=False).sort_index().to_string())


if __name__ == "__main__":
    main()
