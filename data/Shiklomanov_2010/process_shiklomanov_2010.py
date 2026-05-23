#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Shiklomanov_2010"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-05-23"

source_dataset = '''
Shiklomanov, Nikolay I; Streletskiy, Dmitry A; Nelson, Frederick E;
Hollister, Robert D; Romanovsky, Vladimir E; Tweedie, Craig E; Bockheim,
James G; Brown, Jerry (2010): (Table 1) Active-layer thickness as measured
by the Biocomplexity Experiment (BE) for the flooded, drained and control
sections in Barrow, Alaska [dataset]. PANGAEA.
https://doi.org/10.1594/PANGAEA.836769
'''

processing_assumptions = [
  "The PANGAEA tab-delimited export for Table 1 is parsed directly.",
  "Only the Biocomplexity Experiment BE-HED and BE-CCF active-layer-thickness columns are emitted as CUSP observations.",
  "The CALM/ITEX comparison column is not ingested because CUSP treats the standalone CALM source as the source of truth for CALM-family observations.",
  "Each non-missing BE-HED or BE-CCF value is emitted as one source/year/area/subproject observation.",
  "All emitted observations are treated as permafrost-present active-layer-thickness observations, with pf_depth set equal to thaw_depth.",
  "Method is set to unknown because the PANGAEA table describes the source as multiple investigations and does not provide the specific field measurement method for each BE column.",
]

temporal_handling = [
  "The PANGAEA Date/Time field reports year only.",
  "Year-only dates are encoded as September 1 of the reported year, following the project convention for Northern Hemisphere thaw-season observations without a reported month or day.",
]

spatial_handling = [
  "All rows use the single PANGAEA event coordinate for Barrow_Utqiagvik: 71.300000, -156.600000.",
  "The source table does not provide separate coordinates for flooded, drained, or control sections.",
]

manual_steps = [
  "Download PANGAEA_836769.tab from https://doi.pangaea.de/10.1594/PANGAEA.836769?format=textfile."
]

known_limitations = [
  "The source table contains landscape-section annual summary values rather than individual probe points.",
  "No section-specific coordinates are provided.",
  "The CALM/ITEX comparison values in the source table are intentionally excluded to avoid mixing a comparison series with the BE observations and to avoid duplicating CALM-family data already represented through the CALM ingestion.",
]

external_dependencies = [
  "Dataset DOI: 10.1594/PANGAEA.836769",
  "Article DOI: 10.1029/2009JG001248",
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


source = "Shiklomanov_2010"
source_dir = _ROOT_DIR / "data" / source
raw_path = source_dir / "PANGAEA_836769.tab"
output_path = source_dir / f"processed_{source.lower()}.csv"

EVENT_LAT = 71.3
EVENT_LON = -156.6

VALUE_COLUMNS = {
    "ALD [cm] (layer thickness BE-HED)": "BE-HED",
    "ALD [cm] (layer thickness BE-CCF)": "BE-CCF",
}


def find_table_header(path: Path) -> int:
    """Return the zero-based line index of the PANGAEA data table header."""

    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if line.startswith("Date/Time\tArea\t"):
                return index
    raise ValueError(f"Could not find PANGAEA table header in {path}.")


header_index = find_table_header(raw_path)
raw = pd.read_csv(raw_path, sep="\t", skiprows=header_index, dtype=str)

records: list[dict[str, object]] = []
for _, row in raw.iterrows():
    year = int(row["Date/Time"])
    area = str(row["Area"]).strip()
    for value_column, subproject in VALUE_COLUMNS.items():
        thaw_depth = pd.to_numeric(row[value_column], errors="coerce")
        if pd.isna(thaw_depth):
            continue
        records.append(
            {
                "lon": EVENT_LON,
                "lat": EVENT_LAT,
                "date": f"{year:04d}-09-01",
                "source": source,
                "site_id": f"{subproject}_{area}",
                "pf_observed": 1,
                "pf_depth": float(thaw_depth),
                "thaw_depth": float(thaw_depth),
                "obs_limit": np.nan,
                "method": "unknown",
                "source_year": year,
                "source_area": area,
                "source_subproject": subproject,
                "source_event": "Barrow_Utqiagvik",
            }
        )

df_out = pd.DataFrame.from_records(records)
df_out["pf_observed"] = df_out["pf_observed"].astype(int)

data_utils.check_columns(df_out)

df_out.to_csv(output_path, index=False)
