#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "NCSS_Lab_Data_Mart"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk"
last_substantive_update = "2026-05-21"

source_dataset = '''
USDA Natural Resources Conservation Service, National Cooperative Soil Survey
Soil Characterization Database / NCSS Lab Data Mart. Compact CUSP raw extract
generated from ncss_labdatagpkg.zip downloaded from
https://ncsslabdatamart.sc.egov.usda.gov/ on 2026-05-21.
'''

processing_assumptions = [
  "The versioned raw input is a compact pedon-level subset generated from the local NCSS Lab Data Mart GeoPackage by extract_ncss_lab_data_mart_raw.py.",
  "The full NCSS GeoPackage and ZIP archive are intentionally not versioned because they are too large for the repository.",
  "Rows with any f-bearing horizon designation in hzn_desgn or hzn_desgn_old are treated as permafrost/frozen-ground presence observations.",
  "For presence rows, pf_depth is the shallowest top depth among f-bearing horizons.",
  "Rows with no f-bearing horizon designation are treated as absence observations to profile bottom, with obs_limit equal to the deepest horizon bottom.",
  "Absence rows are only retained in the raw extract when abs(latitude) >= 55 degrees to avoid low-latitude absence records that are not useful for CUSP.",
  "Explicit presence rows are retained globally regardless of latitude.",
  "NCSS horizon designation notation is treated as authoritative for frozen-layer status; otherwise the source cannot be used consistently.",
  "The canonical thaw_depth field is left missing because these are pedon/profile frozen-horizon observations, not active-layer-thickness measurements.",
  "Method is assigned as pit, the closest current CUSP vocabulary term for soil pedon/profile descriptions.",
]

temporal_handling = [
  "NCSS site_obsdate is parsed as the observation date and written as YYYY-MM-DD.",
  "Rows missing site_obsdate are excluded during compact raw extract generation.",
]

spatial_handling = [
  "Latitude and longitude are read from NCSS latitude_decimal_degrees and longitude_decimal_degrees.",
  "Rows missing coordinates are excluded during compact raw extract generation.",
]

manual_steps = [
  "Download the zipped GeoPackage from the NCSS Lab Data Mart website.",
  "Place ncss_labdatagpkg.zip in data/NCSS_Lab_Data_Mart/ and extract ncss_labdata.gpkg locally.",
  "Run data/NCSS_Lab_Data_Mart/extract_ncss_lab_data_mart_raw.py to regenerate raw_ncss_permafrost_domain_pedons.csv.",
]

known_limitations = [
  "The compact raw extract is derived from the NCSS GeoPackage and should be regenerated if the NCSS Lab Data Mart release changes.",
  "Absence observations mean permafrost/frozen material was not indicated within the described profile, not that permafrost is absent below the profile bottom.",
  "Some NCSS rows overlap with existing Pastick records; Pastick often carries update-like dates, so coordinate/depth/profile-bottom matching is more informative than exact date matching for that source.",
  "The method field does not distinguish soil pits from auger/core descriptions because the compact NCSS tables do not provide a reliable per-row CUSP method mapping.",
]

external_dependencies = [
  "NCSS Lab Data Mart: https://ncsslabdatamart.sc.egov.usda.gov/",
  "USDA-NRCS soils data are public domain unless otherwise noted by USDA.",
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


source = "NCSS_Lab_Data_Mart"
source_dir = _ROOT_DIR / "data" / source
raw_path = source_dir / "raw_ncss_permafrost_domain_pedons.csv"
output_path = source_dir / "processed_ncss_lab_data_mart.csv"


def clean_text(series: pd.Series) -> pd.Series:
    """Strip strings and normalize empty values."""

    cleaned = series.astype("string").str.strip()
    return cleaned.mask(cleaned == "")


def choose_site_id(df: pd.DataFrame) -> pd.Series:
    """Choose the most stable NCSS identifier available for CUSP site_id."""

    site_id = clean_text(df["upedonid"])
    site_id = site_id.fillna(clean_text(df["usiteid"]))
    site_id = site_id.fillna(clean_text(df["pedlabsampnum"]))
    return site_id.fillna("NCSS_PEDON_" + df["pedon_key"].astype("string"))


def build_processed_table(raw: pd.DataFrame) -> pd.DataFrame:
    """Convert the compact NCSS raw extract into CUSP processed-source rows."""

    df = raw.copy()
    df["candidate_type"] = clean_text(df["candidate_type"]).str.lower()
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df["pf_depth_cm"] = pd.to_numeric(df["pf_depth_cm"], errors="coerce")
    df["obs_limit_cm"] = pd.to_numeric(df["obs_limit_cm"], errors="coerce")
    df["date"] = pd.to_datetime(df["site_obsdate"], errors="coerce", utc=True).dt.date.astype("string")
    df["site_id"] = choose_site_id(df)

    is_presence = df["candidate_type"].eq("presence")
    is_absence = df["candidate_type"].eq("absence")

    if not (is_presence | is_absence).all():
        bad_types = sorted(df.loc[~(is_presence | is_absence), "candidate_type"].dropna().unique())
        raise ValueError(f"Unexpected NCSS candidate_type values: {bad_types}")

    df["pf_observed"] = np.where(is_presence, 1, 0).astype(int)
    df["pf_depth"] = np.where(is_presence, df["pf_depth_cm"], np.nan)
    df["thaw_depth"] = np.nan
    df["obs_limit"] = df["obs_limit_cm"]
    df.loc[is_presence & (df["obs_limit"] <= 0), "obs_limit"] = np.nan
    df["method"] = "pit"
    df["source"] = source

    processed = df.dropna(subset=["lat", "lon", "date"]).copy()
    processed = processed.loc[
        (processed["pf_observed"].eq(1) & processed["pf_depth"].notna())
        | (processed["pf_observed"].eq(0) & processed["obs_limit"].notna() & (processed["obs_limit"] > 0))
    ].copy()

    ordered = [
        "site_id",
        "lat",
        "lon",
        "date",
        "pf_observed",
        "pf_depth",
        "thaw_depth",
        "obs_limit",
        "method",
        "source",
        "candidate_type",
        "absence_latitude_threshold_abs_ge",
        "pedon_key",
        "site_key",
        "pedlabsampnum",
        "upedonid",
        "usiteid",
        "country_key",
        "state_key",
        "county_key",
        "mlra_key",
        "ssa_key",
        "frozen_horizons",
        "all_horizons",
        "n_frozen_layers",
        "n_layers",
        "corr_classification_name",
        "corr_taxorder",
        "corr_taxsuborder",
        "corr_taxgrtgroup",
        "corr_taxsubgrp",
        "samp_classification_name",
        "samp_taxorder",
        "samp_taxsuborder",
        "samp_taxgrtgroup",
        "samp_taxsubgrp",
        "SSL_classification_name",
        "SSL_taxorder",
        "SSL_taxsuborder",
        "SSL_taxgrtgroup",
        "SSL_taxsubgrp",
    ]
    processed = processed[ordered]
    processed = processed.sort_values(["candidate_type", "country_key", "state_key", "site_id"]).reset_index(drop=True)
    return processed


def main() -> None:
    raw = pd.read_csv(raw_path, low_memory=False)
    processed = build_processed_table(raw)
    data_utils.check_columns(processed)
    processed.to_csv(output_path, index=False)

    counts = processed["pf_observed"].value_counts().sort_index().to_dict()
    print(f"Wrote {output_path} with {len(processed)} rows: {counts}")


if __name__ == "__main__":
    main()
