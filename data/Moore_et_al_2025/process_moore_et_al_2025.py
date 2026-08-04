#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Moore_et_al_2025"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-04"
source_dataset = '''
Moore, M.A., K. Schaefer, L.K. Clayton, E.E. Hoy, M. Auclair,
K. Bakian-Dogaheh, M.J. Battaglia, K. Bennett, W.R. Bolton,
L.L. Bourgeau-Chavez, A.E. Bredder, D. Chen, R.H. Chen, A.C. Chen,
J. Chen, D. Chiasson, R. Chitra-tarak, A. Collins, L. Cornette,
J. Dann, E. Devoie, M. Dominico, T.A. Douglas, S. Gagnon, S.E. Grelick,
P. Griffith, J. He, G. Iwahana, E. Jafarov, L.K. Jenkins, E.S. Kasischke,
S. Kim, P.B. Kirchner, B. Lecavalier, J. Ledman, S. Liben, L. Liu,
T.V. Loboda, S. Ludwig, M.J. Macander, N. Matsui, R.J. Michaelides,
M. Moghaddam, S. Natali, S.K. Panda, A.D. Parsekian, M. Pearce,
W. Quinton, A.V. Rocha, H. Rodenhizer, P. Roy-Leveillee, N. Saravanan,
Z. Sauve, S.R. Schaefer, E.A.G. Schuur, O. Sonnentag, T.D. Sullivan,
A. Tabatabaeenejad, L. Thomas, B. Thorne, K. Turner, K. Wang, C.J. Wilson,
H.A. Zebker, T. Zhang, Y. Zhao, and S. Zwieback. 2025.
ABoVE: Soil Moisture and Active Layer Thickness in Alaska, USA and Canada,
2005-2022. ORNL DAAC, Oak Ridge, Tennessee, USA.
https://doi.org/10.3334/ORNLDAAC/2369
'''
processing_assumptions = [
  "ALT == -9999 and rows with missing lat/lon are dropped before aggregation.",
  "Rows matching the original Jafarov_2016 GPR and probe products by method, coordinates rounded to six decimals, and depth rounded to 0.0001 cm are removed before Moore aggregation, irrespective of the conflicting dates in the synthesis table.",
  "Duplicate rows at the same site_name/latitude/longitude/date are averaged for ALT.",
  "Dense retained GPR picks are aggregated to one mean observation per occupied 5 m by 5 m UTM cell within site and survey date; non-GPR observations are not spatially aggregated.",
  "Every retained numeric ALT is treated as a permafrost detection at the reported depth; no arbitrary 130 cm or July 15 presence threshold is applied.",
  "method is inferred from ALT_instrument and mapped to tp or gp when the group is internally consistent; otherwise method is set to unknown.",
]
temporal_handling = [
  "Per-record dates are parsed from the input CSV and kept at the observation level.",
  "The Jafarov copies are removed without using Moore dates because primary documentation and raw-file names establish that the shared observations were collected in August 2013, while Moore assigns those same rows dates in 2014 or 2018.",
]
spatial_handling = [
  "Coordinates are used as provided in the source CSV without reprojection.",
  "GPR aggregation uses a local UTM projection selected independently for each site/date survey unit.",
]
manual_steps = [
  "Download ABoVE_Soil_ThawDepth_Moisture_Validation_V2.csv into data/Moore_et_al_2025 before running the script.",
]
known_limitations = [
  "The source file labels the measurement ALT rather than supplying a separate binary permafrost field, so conversion from numeric ALT to presence is flagged as a source-context state assignment.",
  "The Jafarov source-specific filter is guarded by expected match counts (57,294 GPR and 1,297 probe rows) so a changed input cannot silently alter deduplication.",
  "CALM overlap review found spatial/site-year overlap with CALM but no exact coordinate/date/depth duplicate rows; source documentation indicates ABoVE/SMALT field observations, so Moore_et_al_2025 is treated as independent for now.",
]
external_dependencies = [
  "Gitignored raw input ABoVE_Soil_ThawDepth_Moisture_Validation_V2.csv hosted outside the repo; see EXTERNAL_DATA_SOURCES.md.",
]
notes = ""
"""

import pandas as pd
import numpy as np
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = "Moore_et_al_2025"

INPUT_FILE = _ROOT_DIR / "data" / source / "ABoVE_Soil_ThawDepth_Moisture_Validation_V2.csv"
JAFAROV_DIR = _ROOT_DIR / "data" / "Jafarov_2016"
EXPECTED_JAFAROV_GPR_COPIES = 57_294
EXPECTED_JAFAROV_PROBE_COPIES = 1_297

def coerce_date(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce").dt.date


def _observation_signature(
    lat: pd.Series,
    lon: pd.Series,
    depth_cm: pd.Series,
) -> pd.MultiIndex:
    """Build the stable spatial/depth signature used for source deduplication."""

    signature = pd.DataFrame(
        {
            "lat": pd.to_numeric(lat, errors="coerce").round(6),
            "lon": pd.to_numeric(lon, errors="coerce").round(6),
            # Four decimals remove only representation noise introduced by
            # the source's meter-to-centimeter conversion. Coarser decimal
            # rounding has half-even boundary failures for three exact copies.
            "depth_cm": pd.to_numeric(depth_cm, errors="coerce").round(4),
        }
    )
    return pd.MultiIndex.from_frame(signature)


def _load_jafarov_signatures() -> tuple[pd.MultiIndex, pd.MultiIndex]:
    """Load original-source GPR and probe signatures from Jafarov_2016."""

    gpr = pd.read_csv(JAFAROV_DIR / "lvl1_gpr_alt.csv")
    gpr_signature = _observation_signature(
        gpr["lat_gpr"],
        gpr["lon_gpr"],
        pd.to_numeric(gpr["alt_gpr"], errors="coerce") * 100.0,
    )

    probe = pd.read_csv(
        JAFAROV_DIR / "prb_gpr_alt_hd.csv",
        skiprows=[0, 1, 2, 4],
        header=0,
    )
    probe_signature = _observation_signature(
        probe["lat_prb"],
        probe["lon_prb"],
        pd.to_numeric(probe["alt_prb"], errors="coerce") * 100.0,
    )
    return gpr_signature, probe_signature


def remove_jafarov_copies(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Remove Jafarov observations republished with incorrect Moore dates."""

    gpr_signature, probe_signature = _load_jafarov_signatures()
    moore_signature = _observation_signature(df["latitude"], df["longitude"], df["ALT"])
    instrument = df["ALT_instrument"].astype("string").str.strip().str.lower()
    team = df["team_name"].astype("string").str.strip().str.lower()
    is_schaefer = team.eq("schaefer")
    gpr_copies = instrument.eq("gpr") & is_schaefer & moore_signature.isin(gpr_signature)
    probe_copies = instrument.eq("probe") & is_schaefer & moore_signature.isin(probe_signature)

    counts = {
        "gpr": int(gpr_copies.sum()),
        "probe": int(probe_copies.sum()),
    }
    expected = {
        "gpr": EXPECTED_JAFAROV_GPR_COPIES,
        "probe": EXPECTED_JAFAROV_PROBE_COPIES,
    }
    if counts != expected:
        raise RuntimeError(
            "Moore/Jafarov deduplication match counts changed: "
            f"found {counts}, expected {expected}. Review the source files before proceeding."
        )

    return df.loc[~(gpr_copies | probe_copies)].copy(), counts

def main():
    df = pd.read_csv(INPUT_FILE, low_memory=False)

    # Drop invalid ALT
    df = df[df["ALT"] != -9999]
    #drop missing lat and lon
    df = df[df["latitude"] != -9999]
    df = df[df["longitude"] != -9999]

    df, removed_jafarov = remove_jafarov_copies(df)

    # Parse dates
    df["_date"] = coerce_date(df["date"])
    df = df.dropna(subset=["_date"])

       

    # keys should already be defined as:
    keys = ["site_name", "latitude", "longitude", "_date"]
    
    if "ALT_instrument" in df.columns:
        instrument = df["ALT_instrument"].astype("string").str.strip().str.lower()
        df["_instrument_method"] = instrument.map(
            {
                "probe": "tp",
                "thermal probe": "tp",
                "thaw probe": "tp",
                "gpr": "gp",
                "ground penetrating radar": "gp",
            }
        )
        unknown_instrument = instrument.notna() & instrument.ne("") & df["_instrument_method"].isna()
        df.loc[unknown_instrument, "_instrument_method"] = "unknown"
    else:
        df["_instrument_method"] = pd.NA

    # Vectorized grouping avoids one Python callback per nearly unique point.
    result = (
        df.groupby(keys, dropna=False, as_index=False)
        .agg(
            _thaw_depth=("ALT", "mean"),
            _native_count=("ALT", "size"),
            _method_nunique=("_instrument_method", "nunique"),
            _method_first=("_instrument_method", "first"),
            _team_nunique=("team_name", "nunique"),
            _team_first=("team_name", "first"),
        )
    )
    result["_method"] = result["_method_first"].where(
        result["_method_nunique"].eq(1),
        "unknown",
    ).fillna("unknown")
    result["team_name_out"] = result["_team_first"].where(result["_team_nunique"].eq(1), pd.NA)

    # Build output
    site_part = result["site_name"].astype(str)
    team_part = result["team_name_out"].fillna("").astype(str)  # avoids "_<NA>" in IDs
    site_id = site_part.where(team_part.eq(""), site_part + "_" + team_part)
    out = pd.DataFrame({
        "site_id": site_id,
        "date": result["_date"].astype("string"),
        "lat": result["latitude"],
        "lon": result["longitude"],
        "thaw_depth": result["_thaw_depth"],
        "method": result["_method"],
        "source": source,
        "quality_flag_summary_statistic": result["_native_count"].gt(1),
        "quality_flag_pf_state_assumed": True,
        "_native_count": result["_native_count"],
    })

    gpr_mask = out["method"].eq("gp")
    gpr = data_utils.aggregate_gpr_points(
        out.loc[gpr_mask].copy(),
        spacing_m=5.0,
        native_count_column="_native_count",
    )
    non_gpr = out.loc[~gpr_mask].drop(columns="_native_count").copy()
    out = pd.concat([gpr, non_gpr], ignore_index=True, sort=False)

    out["pf_observed"] = pd.Series(1, index=out.index, dtype="Int64")
    out["pf_depth"] = out["thaw_depth"]
    out["obs_limit"] = np.nan

    # Final column order
    core_columns = [
        "site_id", "date", "lat", "lon", "thaw_depth", "pf_observed",
        "pf_depth", "obs_limit", "method", "source",
    ]
    provenance_columns = [
        "gpr_native_count", "gpr_aggregation_spacing_m",
        "quality_flag_summary_statistic", "quality_flag_pf_state_assumed",
    ]
    out = out[core_columns + provenance_columns]
    
    data_utils.check_columns(out)

    out.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
    print(
        f"Removed {removed_jafarov['gpr']:,} Jafarov GPR and "
        f"{removed_jafarov['probe']:,} Jafarov probe copies; wrote {len(out):,} rows."
    )

if __name__ == "__main__":
    main()
