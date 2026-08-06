#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metadata_schema_version = 1
source_key = "Moore_et_al_2025"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-06"
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

Correction provenance:
Douglas, T.A. 2019. ABoVE: Soil Active Layer Thaw Depths at CRREL sites near
Fairbanks, Alaska, 2014-2018. ORNL DAAC, Oak Ridge, Tennessee, USA.
https://doi.org/10.3334/ORNLDAAC/1701

Douglas, T.A. 2021. Repeat active layer depths at sites near Fairbanks,
Alaska (Version 1). Zenodo.
https://doi.org/10.5281/zenodo.4670463
'''
processing_assumptions = [
  "ALT == -9999 and rows with missing lat/lon are dropped before aggregation.",
  "Rows matching the original Jafarov_2016 GPR and probe products by method, coordinates rounded to six decimals, and depth rounded to 0.0001 cm are removed before Moore aggregation, irrespective of the conflicting dates in the synthesis table.",
  "All valid rows attributed to the Natali team are removed before aggregation because the direct Natali_2023 release contains the underlying 2016-2018 transect observations with their actual dates.",
  "Malformed Douglas Farmers Loop dates are decoded with an explicit source-specific mapping after annual depth vectors are checked against the original Douglas workbook.",
  "Douglas Farmers Loop station numbers and coordinates are restored from the official ORNL DAAC point geometry because the synthesis import removed zeroes from station identifiers and collapsed distinct stations such as 1, 10, and 100.",
  "Duplicate rows at the same site_name/latitude/longitude/date are averaged for ALT.",
  "Dense retained GPR picks are aggregated to one mean observation per occupied 5 m by 5 m UTM cell within site and survey date; non-GPR observations are not spatially aggregated.",
  "Every retained numeric ALT is treated as a permafrost detection at the reported depth; no arbitrary 130 cm or July 15 presence threshold is applied.",
  "method is inferred from ALT_instrument and mapped to tp or gp when the group is internally consistent; otherwise method is set to unknown.",
]
temporal_handling = [
  "Per-record dates are parsed from the input CSV and kept at the observation level outside the documented Douglas Farmers Loop import error.",
  "For malformed Farmers Loop dates, the real month and day are decoded from the synthesis field and the thaw year is recovered by matching each annual depth vector to the original Douglas 2014-2020 workbook; the 2022 T1 year follows the source sequence and stated 2005-2022 coverage and is flagged as approximate.",
  "The Jafarov copies are removed without using Moore dates because primary documentation and raw-file names establish that the shared observations were collected in August 2013, while Moore assigns those same rows dates in 2014 or 2018.",
]
spatial_handling = [
  "Coordinates outside the Douglas Farmers Loop transects are used as provided in the source CSV without reprojection.",
  "Farmers Loop T1 and T2 coordinates are restored from the 2014 station sequence in the official ORNL DAAC EPSG:26906 point geometry and transformed to WGS84.",
  "GPR aggregation uses a local UTM projection selected independently for each site/date survey unit.",
]
manual_steps = [
  "Download ABoVE_Soil_ThawDepth_Moisture_Validation_V2.csv into data/Moore_et_al_2025 before running the script.",
]
known_limitations = [
  "The source file labels the measurement ALT rather than supplying a separate binary permafrost field, so conversion from numeric ALT to presence is flagged as a source-context state assignment.",
  "The Jafarov source-specific filter is guarded by expected match counts (57,294 GPR and 1,297 probe rows) so a changed input cannot silently alter deduplication.",
  "The Natali filter is guarded at 1,962 valid synthesis rows; Moore assigns all of them the implausible date 2013-08-11, while the direct source records their 2016-2018 campaign dates.",
  "The Farmers Loop repair is guarded at 1,488 corrected date rows and 1,917 coordinate-restored rows. Fourteen 2014-2020 site-year depth vectors match the older Douglas deposit exactly except for one T1 2016 value; the newer Moore value is retained for that point.",
  "The T1 date 2022-09-17 is decoded from the malformed month/day field and assigned to the otherwise missing 2022 block based on the source sequence and stated temporal coverage; those rows carry date_source_approximate.",
  "Rows assigned that approximate 2022 date carry both date_assigned and date_source_approximate; validated workbook date corrections carry only the source-code-recoded flag.",
  "CALM overlap review found spatial/site-year overlap with CALM but no exact coordinate/date/depth duplicate rows; source documentation indicates ABoVE/SMALT field observations, so Moore_et_al_2025 is treated as independent for now.",
]
external_dependencies = [
  "Gitignored raw input ABoVE_Soil_ThawDepth_Moisture_Validation_V2.csv hosted outside the repo; see EXTERNAL_DATA_SOURCES.md.",
]
notes = "The committed Douglas workbook and ORNL DAAC geometry archive are small primary-source companions used only to validate and repair the affected Farmers Loop rows."
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from cusp.data_utils import _ROOT_DIR
from cusp import data_utils

source = "Moore_et_al_2025"

INPUT_FILE = _ROOT_DIR / "data" / source / "ABoVE_Soil_ThawDepth_Moisture_Validation_V2.csv"
JAFAROV_DIR = _ROOT_DIR / "data" / "Jafarov_2016"
FARMERS_LOOP_ACTIVE_LAYER_FILE = (
    _ROOT_DIR / "data" / source / "Active layer measurements 2014 to 2020.xlsx"
)
FARMERS_LOOP_GEOMETRY_FILE = (
    _ROOT_DIR / "data" / source / "active_layer_thaw_depths_all_sites.zip"
)
EXPECTED_JAFAROV_GPR_COPIES = 57_294
EXPECTED_JAFAROV_PROBE_COPIES = 1_297
EXPECTED_NATALI_COPIES = 1_962
EXPECTED_FARMERS_LOOP_CORRECTED_DATES = 1_488
EXPECTED_FARMERS_LOOP_COORDINATES = 1_917

FARMERS_LOOP_SPECS = {
    "Farmers-T1": {
        "plot_prefix": "Farmers-T1",
        "geometry_site": "Farmer's Loop Transect 1",
        "workbook_sheet": "Farmers1",
        "station_count": 101,
    },
    "FarmersT2": {
        "plot_prefix": "Farmers-T2",
        "geometry_site": "Farmer's Loop Transect 2",
        "workbook_sheet": "Farmers2",
        "station_count": 126,
    },
}

# The source date parser consumed FL1/FL2 as the month, the real month as the
# day, and the real day as the two-digit year, while dropping the real year.
FARMERS_LOOP_DATE_CORRECTIONS = {
    ("Farmers-T1", "2007-01-10"): "2014-10-07",
    ("Farmers-T1", "2019-01-09"): "2015-09-19",
    ("Farmers-T1", "2010-01-10"): "2016-10-10",
    ("Farmers-T1", "2014-01-10"): "2019-10-14",
    ("Farmers-T1", "2005-01-10"): "2020-10-05",
    ("Farmers-T1", "2017-01-09"): "2022-09-17",
    ("FarmersT2", "2007-02-10"): "2014-10-07",
    ("FarmersT2", "2019-02-09"): "2015-09-19",
    ("FarmersT2", "2011-02-10"): "2016-10-11",
    ("FarmersT2", "2017-02-10"): "2017-10-17",
    ("FarmersT2", "2010-02-10"): "2018-10-10",
    ("FarmersT2", "2014-02-10"): "2019-10-14",
    ("FarmersT2", "2005-02-10"): "2020-10-05",
}

FARMERS_LOOP_YEAR_VALIDATION = {
    ("Farmers-T1", "2007-01-10"): 2014,
    ("Farmers-T1", "2019-01-09"): 2015,
    ("Farmers-T1", "2010-01-10"): 2016,
    ("Farmers-T1", "2017-10-03"): 2017,
    ("Farmers-T1", "2018-10-10"): 2018,
    ("Farmers-T1", "2014-01-10"): 2019,
    ("Farmers-T1", "2005-01-10"): 2020,
    ("FarmersT2", "2007-02-10"): 2014,
    ("FarmersT2", "2019-02-09"): 2015,
    ("FarmersT2", "2011-02-10"): 2016,
    ("FarmersT2", "2017-02-10"): 2017,
    ("FarmersT2", "2010-02-10"): 2018,
    ("FarmersT2", "2014-02-10"): 2019,
    ("FarmersT2", "2005-02-10"): 2020,
}


def _farmers_loop_station_order(station_count: int) -> list[int]:
    """Recover source station order after zeroes were removed from IDs."""

    return sorted(
        range(1, station_count + 1),
        key=lambda station: (int(str(station).replace("0", "")), station),
    )


def _farmers_loop_plot_label(site_name: str, station: int) -> str:
    """Return the Moore plot label for an original-source station ordinal."""

    spec = FARMERS_LOOP_SPECS[site_name]
    if site_name == "FarmersT2" and station == 74:
        suffix = "73A"
    elif site_name == "FarmersT2" and station == 75:
        suffix = "74"
    else:
        suffix = str(station).replace("0", "")
    return f"{spec['plot_prefix']}-{suffix}"


def _load_farmers_loop_coordinates() -> dict[str, pd.DataFrame]:
    """Load observation-specific Farmers Loop coordinates from ORNL DAAC."""

    archive = FARMERS_LOOP_GEOMETRY_FILE.resolve().as_posix()
    layer = "active_layer_thaw_depths_all_sites/active_layer_thaw_depths_all_sites.shp"
    geometry = gpd.read_file(f"zip://{archive}!{layer}")
    if geometry.crs is None:
        raise RuntimeError("Farmers Loop correction geometry has no CRS.")
    geometry = geometry.loc[geometry["year"].eq(2014)].to_crs(4326)

    lookups: dict[str, pd.DataFrame] = {}
    for site_name, spec in FARMERS_LOOP_SPECS.items():
        site_geometry = geometry.loc[
            geometry["site"].eq(spec["geometry_site"])
        ].reset_index(drop=True)
        expected_count = int(spec["station_count"])
        if len(site_geometry) != expected_count:
            raise RuntimeError(
                f"Expected {expected_count} ORNL coordinates for {site_name}; "
                f"found {len(site_geometry)}."
            )
        lookups[site_name] = pd.DataFrame(
            {
                "station": np.arange(1, expected_count + 1),
                "lat": site_geometry.geometry.y.to_numpy(),
                "lon": site_geometry.geometry.x.to_numpy(),
            }
        ).set_index("station")
    return lookups


def _validate_farmers_loop_year_mapping(df: pd.DataFrame) -> None:
    """Confirm corrected thaw years against Douglas's original annual vectors."""

    workbooks = {
        site_name: pd.read_excel(
            FARMERS_LOOP_ACTIVE_LAYER_FILE,
            sheet_name=str(spec["workbook_sheet"]),
        )
        for site_name, spec in FARMERS_LOOP_SPECS.items()
    }
    expected_mismatches = {("Farmers-T1", 2016): 1}

    for (site_name, source_date), year in FARMERS_LOOP_YEAR_VALIDATION.items():
        group = df.loc[
            df["site_name"].eq(site_name)
            & df["date"].astype("string").eq(source_date)
        ]
        station_count = int(FARMERS_LOOP_SPECS[site_name]["station_count"])
        if len(group) != station_count:
            raise RuntimeError(
                f"Expected {station_count} Moore rows for {site_name}/{source_date}; "
                f"found {len(group)}."
            )

        station_order = _farmers_loop_station_order(station_count)
        year_suffix = str(year)[-2:]
        expected_depths = pd.to_numeric(
            workbooks[site_name][f"Thaw_{year_suffix}"], errors="coerce"
        ).to_numpy(dtype=float)[np.asarray(station_order) - 1]
        observed_depths = pd.to_numeric(group["ALT"], errors="coerce").to_numpy(dtype=float)
        mismatch_count = int(
            (~np.isclose(observed_depths, expected_depths, equal_nan=True)).sum()
        )
        expected_mismatch_count = expected_mismatches.get((site_name, year), 0)
        if mismatch_count != expected_mismatch_count:
            raise RuntimeError(
                f"Douglas depth-vector validation changed for {site_name}/{year}: "
                f"found {mismatch_count} mismatches, expected {expected_mismatch_count}."
            )


def repair_farmers_loop_import(df: pd.DataFrame) -> pd.DataFrame:
    """Repair malformed Douglas dates and zero-stripped station coordinates."""

    repaired = df.copy()
    repaired["_date_repaired"] = False
    repaired["_date_source_approximate"] = False
    repaired["_coord_repaired"] = False

    _validate_farmers_loop_year_mapping(repaired)

    source_dates = repaired["date"].astype("string")
    corrected_rows = 0
    for (site_name, source_date), corrected_date in FARMERS_LOOP_DATE_CORRECTIONS.items():
        mask = repaired["site_name"].eq(site_name) & source_dates.eq(source_date)
        expected_count = int(FARMERS_LOOP_SPECS[site_name]["station_count"])
        found_count = int(mask.sum())
        if found_count != expected_count:
            raise RuntimeError(
                f"Expected {expected_count} date repairs for {site_name}/{source_date}; "
                f"found {found_count}."
            )
        repaired.loc[mask, "date"] = corrected_date
        repaired.loc[mask, "_date_repaired"] = True
        if corrected_date == "2022-09-17":
            repaired.loc[mask, "_date_source_approximate"] = True
        corrected_rows += found_count

    if corrected_rows != EXPECTED_FARMERS_LOOP_CORRECTED_DATES:
        raise RuntimeError(
            f"Expected {EXPECTED_FARMERS_LOOP_CORRECTED_DATES} Farmers Loop date repairs; "
            f"found {corrected_rows}."
        )

    coordinate_lookups = _load_farmers_loop_coordinates()
    coordinate_rows = 0
    farmers_mask = repaired["site_name"].isin(FARMERS_LOOP_SPECS)
    for (site_name, date), group in repaired.loc[farmers_mask].groupby(
        ["site_name", "date"], sort=False
    ):
        spec = FARMERS_LOOP_SPECS[site_name]
        station_count = int(spec["station_count"])
        if len(group) != station_count:
            raise RuntimeError(
                f"Expected {station_count} valid Farmers Loop rows for {site_name}/{date}; "
                f"found {len(group)}."
            )

        station_order = _farmers_loop_station_order(station_count)
        expected_plots = [
            _farmers_loop_plot_label(site_name, station)
            for station in station_order
        ]
        observed_plots = group["plot"].astype("string").tolist()
        if observed_plots != expected_plots:
            raise RuntimeError(
                f"Farmers Loop station order changed for {site_name}/{date}; "
                "the coordinate repair cannot be applied safely."
            )

        replacement = coordinate_lookups[site_name].loc[station_order]
        anchor_mask = np.asarray(["0" not in str(station) for station in station_order])
        observed_anchor_lat = pd.to_numeric(
            group.loc[anchor_mask, "latitude"], errors="coerce"
        ).to_numpy(dtype=float)
        observed_anchor_lon = pd.to_numeric(
            group.loc[anchor_mask, "longitude"], errors="coerce"
        ).to_numpy(dtype=float)
        replacement_anchor = replacement.iloc[anchor_mask]
        max_anchor_delta = max(
            float(np.max(np.abs(observed_anchor_lat - replacement_anchor["lat"].to_numpy()))),
            float(np.max(np.abs(observed_anchor_lon - replacement_anchor["lon"].to_numpy()))),
        )
        if max_anchor_delta > 2.0e-6:
            raise RuntimeError(
                f"ORNL coordinate ordering no longer matches {site_name}/{date}; "
                f"maximum anchor delta is {max_anchor_delta:.8f} degrees."
            )

        repaired.loc[group.index, "latitude"] = replacement["lat"].to_numpy()
        repaired.loc[group.index, "longitude"] = replacement["lon"].to_numpy()
        repaired.loc[group.index, "_coord_repaired"] = True
        coordinate_rows += len(group)

    if coordinate_rows != EXPECTED_FARMERS_LOOP_COORDINATES:
        raise RuntimeError(
            f"Expected {EXPECTED_FARMERS_LOOP_COORDINATES} Farmers Loop coordinate repairs; "
            f"found {coordinate_rows}."
        )
    return repaired

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


def remove_natali_copies(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Remove direct Natali transects republished with a false Moore date."""

    team = df["team_name"].astype("string").str.strip().str.lower()
    copies = team.eq("natali")
    count = int(copies.sum())
    if count != EXPECTED_NATALI_COPIES:
        raise RuntimeError(
            f"Expected {EXPECTED_NATALI_COPIES:,} valid Moore/Natali copies; "
            f"found {count:,}. Review the source files before proceeding."
        )
    return df.loc[~copies].copy(), count

def main():
    df = pd.read_csv(INPUT_FILE, low_memory=False)

    # Drop invalid ALT
    df = df[df["ALT"] != -9999]
    #drop missing lat and lon
    df = df[df["latitude"] != -9999]
    df = df[df["longitude"] != -9999]

    df, removed_jafarov = remove_jafarov_copies(df)
    df, removed_natali = remove_natali_copies(df)
    df = repair_farmers_loop_import(df)

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
            _date_repaired=("_date_repaired", "any"),
            _date_source_approximate=("_date_source_approximate", "any"),
            _coord_repaired=("_coord_repaired", "any"),
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
        "quality_flag_source_unit_or_code_recoded": result["_date_repaired"],
        "quality_flag_date_assigned": result["_date_source_approximate"],
        "quality_flag_date_source_approximate": result["_date_source_approximate"],
        "quality_flag_coord_lookup_or_interpolated": result["_coord_repaired"],
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
        "quality_flag_summary_statistic",
        "quality_flag_source_unit_or_code_recoded",
        "quality_flag_date_assigned",
        "quality_flag_date_source_approximate",
        "quality_flag_coord_lookup_or_interpolated",
    ]
    out = out[core_columns + provenance_columns]
    
    data_utils.check_columns(out)

    out.to_csv(_ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False)
    print(
        f"Removed {removed_jafarov['gpr']:,} Jafarov GPR and "
        f"{removed_jafarov['probe']:,} Jafarov probe copies plus "
        f"{removed_natali:,} Natali copies; repaired "
        f"{EXPECTED_FARMERS_LOOP_CORRECTED_DATES:,} Farmers Loop dates and "
        f"{EXPECTED_FARMERS_LOOP_COORDINATES:,} coordinates; wrote {len(out):,} rows."
    )

if __name__ == "__main__":
    main()
