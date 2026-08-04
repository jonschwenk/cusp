#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Jafarov_2016"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-04"
source_dataset = '''
Jafarov, E.; Parsekian, A.; Schaefer, K.; Liu, L.; Chen, A.; Panda, S.K.;
Zhang, T. 2018. Pre-ABoVE: Active Layer Thickness and Soil Water Content,
Barrow, Alaska, 2013. ORNL DAAC. https://doi.org/10.3334/ORNLDAAC/1355
'''
processing_assumptions = [
  "The complete level-1 GPR product is read from lvl1_gpr_alt.csv; the high-density comparison table is used only for its mechanical-probe observations because its GPR subset is already represented in the level-1 product.",
  "Probe and GPR active-layer-thickness values are converted from meters to centimeters.",
  "Dense GPR picks are aggregated to one mean observation per occupied 5 m by 5 m UTM cell within site and survey date; probe observations are not spatially aggregated.",
  "All processed observations are treated as permafrost-present, so pf_observed is fixed to 1 and pf_depth is set equal to thaw_depth.",
  "method is set to tp for probe rows and gp for GPR rows.",
]
temporal_handling = [
  "Official documentation and raw-file names establish that the campaign occurred from 2013-08-10 through 2013-08-15.",
  "The processed source tables do not provide a reliable observation date for every point, so all rows are assigned the representative campaign midpoint 2013-08-12 and carry the date_assigned quality flag.",
]
spatial_handling = [
  "Probe and GPR coordinates are taken from their respective source tables without source-coordinate interpolation.",
  "GPR aggregation uses a local UTM projection selected independently for each site/date survey unit.",
]
manual_steps = []
known_limitations = [
  "Observation day is approximate, but the 2013 thaw year is established by the dataset documentation and raw-file names.",
  "The script assumes all retained observations come from continuous permafrost terrain and therefore does not represent non-permafrost cases.",
  "Moore_et_al_2025 republishes 57,294 native GPR picks and 1,297 probe observations from this source with dates assigned to 2014 or 2018. The Moore processor removes those copies before aggregation and retains Jafarov_2016, whose primary documentation establishes the 2013 thaw year, as the original source.",
]
external_dependencies = []
notes = ""
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from cusp import data_utils
from cusp.data_utils import _ROOT_DIR


SOURCE = "Jafarov_2016"
SOURCE_DIR = _ROOT_DIR / "data" / SOURCE
CAMPAIGN_DATE = "2013-08-12"


def _numeric_rows(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for column in columns:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    return out.dropna(subset=columns).copy()


def build_gpr_observations() -> pd.DataFrame:
    """Load and aggregate the complete Jafarov level-1 GPR product."""

    raw = pd.read_csv(SOURCE_DIR / "lvl1_gpr_alt.csv")
    raw = _numeric_rows(raw, ["lat_gpr", "lon_gpr", "alt_gpr"])
    raw = raw.loc[raw["alt_gpr"].ne(-999)].copy()
    gpr = pd.DataFrame(
        {
            "site_id": raw["site_ID"].astype("string"),
            "date": CAMPAIGN_DATE,
            "lat": raw["lat_gpr"],
            "lon": raw["lon_gpr"],
            "thaw_depth": raw["alt_gpr"] * 100.0,
            "method": "gp",
            "source": SOURCE,
            "quality_flag_date_assigned": True,
        }
    )
    gpr = data_utils.aggregate_gpr_points(gpr, spacing_m=5.0)
    gpr["pf_observed"] = 1
    gpr["pf_depth"] = gpr["thaw_depth"]
    gpr["obs_limit"] = np.nan
    return gpr


def build_probe_observations() -> pd.DataFrame:
    """Load the high-density mechanical-probe comparison observations."""

    raw = pd.read_csv(
        SOURCE_DIR / "prb_gpr_alt_hd.csv",
        skiprows=[0, 1, 2, 4],
        header=0,
    )
    raw = _numeric_rows(raw, ["lat_prb", "lon_prb", "alt_prb"])
    raw = raw.loc[raw["alt_prb"].ne(-999)].copy()
    probe = pd.DataFrame(
        {
            "site_id": raw["site_ID"].astype("string"),
            "date": CAMPAIGN_DATE,
            "lat": raw["lat_prb"],
            "lon": raw["lon_prb"],
            "thaw_depth": raw["alt_prb"] * 100.0,
            "pf_observed": 1,
            "pf_depth": raw["alt_prb"] * 100.0,
            "obs_limit": np.nan,
            "method": "tp",
            "source": SOURCE,
            "quality_flag_date_assigned": True,
        }
    )
    return probe


def main() -> None:
    gpr = build_gpr_observations()
    probe = build_probe_observations()
    combined = pd.concat([gpr, probe], ignore_index=True, sort=False)

    data_utils.check_columns(combined)
    output_path = SOURCE_DIR / f"processed_{SOURCE.lower()}.csv"
    combined.to_csv(output_path, index=False)
    print(
        f"Wrote {len(combined):,} rows to {output_path} "
        f"({len(gpr):,} aggregated GPR; {len(probe):,} probe)."
    )


if __name__ == "__main__":
    main()
