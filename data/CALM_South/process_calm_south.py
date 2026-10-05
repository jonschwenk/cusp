"""
metadata_schema_version = 1
source_key = "CALM_South"
release_clearance = "approved"
permission_basis = "other"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-10-05"
source_dataset = '''
CALM network: CALM South Summary Data, original annual workbook, retrieved
2026-10-05. https://www2.gwu.edu/~calm/data/CALM_S_Summary.xls
Site metadata: https://www2.gwu.edu/~calm/data/south.htm
Secondary coordinate/method evidence: GTN-P site metadata and Streletskiy
(2026), https://doi.org/10.6084/m9.figshare.32885756.v1; see site_overrides.json.
'''
processing_assumptions = [
  "Annual end-of-season thaw depths are centimeters. Positive exact values imply presence, with thaw_depth = pf_depth = ALT. Grid/transect entries are spatial means; borehole entries are annual point summaries.",
  "Blank and dash entries are missing. Two zero values (A25 2015 and A7 2018) are excluded: neither establishes presence nor absence with a usable observation limit.",
  "Nine A11 Granite Harbour 90+ entries are lower-bound absence observations with obs_limit = 90 cm, supported by CALM site metadata describing temperature monitoring to 90 cm. Two A15B >130 entries use the analogous explicit lower-bound convention; exact depths remain null.",
  "The workbook legend maps T/B to temp, P and numeric grid sizes to tp, and TT to tt. Mixed codes use documented site-specific assignments and the method_approximate_or_unknown flag, not the font colors (the archived workbook does not reliably distinguish them).",
  "One annual record per normalized site code/year is required; unexpected duplicates or unrecognized nonmissing cells fail rather than being silently discarded.",
  "This original workbook takes precedence over all Southern Hemisphere rows in Streletskiy_2026. All 270 positive southern site-years in the Figshare extract are represented here, plus 156 other positive site-years and 11 bounds. Existing CALM is Northern Hemisphere only; no observations are replaced.",
  "Cross-source spatial screening does not remove independent soil-pit observations or different years/methods. No proximity-only deduplication is performed.",
]
temporal_handling = [
  "Only source year labels are reported. Encode YYYY-02-01 as an explicitly assigned Southern Hemisphere summer placeholder, not a measured survey date; retain calm_year and flag date_assigned. Season start/end interpretation is not inferred from this placeholder.",
]
spatial_handling = [
  "Read workbook decimal degrees or valid degrees/minutes/seconds. Retain raw coordinate strings and site-level coordinates; no new grid-node positions are fabricated.",
  "Six site coordinate overrides are documented with reference URLs in site_overrides.json; flag coord_lookup_or_interpolated, coord_source_flagged, and source_unit_or_code_recoded. A24 and A29 use representative native GTN-P station coordinates; A15A uses Mount Reina Sofia metadata; A16, A26, and A17A use versioned Figshare metadata.",
  "SA2C coordinate disagreement between workbook, Figshare, and GTN-P remains unresolved; retain workbook coordinates with coord_source_flagged rather than choosing a different position silently.",
]
manual_steps = [
  "Download CALM_S_Summary.xls without modifying the original workbook; the retained SHA-256 snapshot is checked by the processor. Metadata evidence snapshots are preserved alongside the workbook.",
]
known_limitations = [
  "The original CALM-South workbook is publicly downloadable, but an explicit original-workbook reuse license was not found. Maintainer authorization is recorded separately from this unresolved licensing evidence; Figshare CC BY 4.0 does not automatically license the original workbook.",
  "These are annual site-level summaries, not individual grid-node or dense temperature time-series observations. Method assignments are site-level and may not capture changes between years.",
  "Coordinates and year-only dates are approximate; especially the station-level coordinate lookups must not be interpreted as surveyed grid locations.",
]
external_dependencies = [
  "xlrd from the source-processing extra; read with its native workbook API (compatible with the repository's xlrd 1.2 pin).",
]
notes = "Issue #36. Maintainer explicitly authorized finalization into CUSP on 2026-10-05 after the scientific and permission caveats were reported. Permission basis other records the public CALM network summary and that maintainer decision, not an inferred CC BY license or provider permission grant. Approval does not publish a new CUSP release."
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from cusp import data_utils

HERE = Path(__file__).resolve().parent
RAW_SHA256 = "895f2f6e91773b832a9714e649df9301efcbb3b00ba3b818e81b49e2c6663a90"


def parse_coordinate(value: object, axis: str) -> float:
    text = str(value).strip().upper()
    if axis not in {"lat", "lon"}:
        raise ValueError(f"Unknown coordinate axis: {axis}")
    maximum = 90 if axis == "lat" else 180
    if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", text):
        result = float(text)
    else:
        hemisphere = text[-1:]
        allowed = "NS" if axis == "lat" else "EW"
        if not hemisphere or hemisphere not in allowed:
            raise ValueError(f"Missing/invalid hemisphere: {value!r}")
        body = text[:-1].strip()
        if "+" in body or "-" in body:
            raise ValueError(f"Signed coordinate with hemisphere suffix: {value!r}")
        dotted = re.fullmatch(r"(\d+)\.(\d+)\.(\d+(?:\.\d+)?)", body)
        parts = list(dotted.groups()) if dotted else re.findall(r"\d+(?:\.\d+)?", body)
        if not 1 <= len(parts) <= 3:
            raise ValueError(f"Invalid coordinate: {value!r}")
        degrees, *fractions = map(float, parts)
        if fractions and (degrees % 1 or any(not 0 <= item < 60 for item in fractions)):
            raise ValueError(f"Invalid DMS minutes/seconds: {value!r}")
        result = degrees + sum(item / (60 ** (index + 1)) for index, item in enumerate(fractions))
        if hemisphere in "SW":
            result = -result
    if not np.isfinite(result) or not -maximum <= result <= maximum:
        raise ValueError(f"Out-of-range coordinate: {value!r}")
    return result


def parse_depth(value: object) -> tuple[str, float]:
    text = str(value).strip()
    if text in {"", "-"}:
        return "missing", np.nan
    match = re.fullmatch(r"(?P<prefix>>\s*)?(?P<depth>\d+(?:\.\d+)?)(?P<suffix>\+)?", text)
    if not match:
        raise ValueError(f"Unrecognized ALT cell: {value!r}")
    depth = float(match["depth"])
    if depth == 0:
        return "zero_unresolved", depth
    return ("lower" if match["prefix"] or match["suffix"] else "exact"), depth


def method_from_code(value: object) -> str:
    text = str(value).strip().upper()
    if re.fullmatch(r"T/B(?:\d+(?:\.\d+)?)?", text):
        return "temp"
    if text == "TT":
        return "tt"
    if re.fullmatch(r"\d+(?:\.\d+)?", text) or "P" in text.split("/") or text == "P,C":
        return "tp"
    return "unknown"


def read_workbook(path: Path) -> pd.DataFrame:
    import xlrd

    book = xlrd.open_workbook(str(path))
    sheet = book.sheet_by_name("south")
    year_headers = [sheet.row_values(row)[6:] for row in range(sheet.nrows) if sheet.cell_value(row, 6) == 1990]
    if not year_headers or any(header != list(range(1990, 2026)) for header in year_headers):
        raise ValueError("Unexpected CALM-South year columns; review the updated workbook.")
    records = []
    for row_number in range(sheet.nrows):
        row = sheet.row_values(row_number)
        code = re.sub(r"\s+", "", str(row[0])).upper()
        if not re.fullmatch(r"(?:SA|A)\d+[A-Z]?", code):
            continue
        for year, value in zip(range(1990, 2026), row[6:], strict=True):
            records.append({
                "calm_site_code": code, "calm_site_name": row[1],
                "calm_lat_raw": str(row[2]), "calm_lon_raw": str(row[3]),
                "calm_elevation_m": row[4], "calm_method_raw": str(row[5]),
                "calm_year": year, "calm_ald_raw": str(value).strip(),
                "calm_workbook_row": row_number + 1,
            })
    raw = pd.DataFrame(records)
    if raw.duplicated(["calm_site_code", "calm_year"]).any():
        raise ValueError("Duplicate CALM-South site/year; do not discard independent observations.")
    return raw


def build_processed_table(raw: pd.DataFrame, overrides: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    audit = raw.copy().reset_index(drop=True)
    parsed = audit["calm_ald_raw"].map(parse_depth)
    audit["calm_ald_bound_type"] = [item[0] for item in parsed]
    audit["calm_ald_cm"] = [item[1] for item in parsed]
    audit["decision"] = audit["calm_ald_bound_type"].map({
        "exact": "retained", "lower": "retained", "missing": "missing", "zero_unresolved": "zero_unresolved",
    })
    result = audit.loc[audit["decision"].eq("retained")].drop(columns="decision").copy()
    coords = []
    methods = []
    for row in result.itertuples(index=False):
        override = overrides.get(row.calm_site_code, {})
        coords.append((override["lat"], override["lon"]) if "lat" in override else (
            parse_coordinate(row.calm_lat_raw, "lat"), parse_coordinate(row.calm_lon_raw, "lon"),
        ))
        methods.append(override.get("method", method_from_code(row.calm_method_raw)))
    result[["lat", "lon"]] = coords
    result["method"] = methods
    result["source"] = "CALM_South"
    result["site_id"] = "CALM_" + result["calm_site_code"]
    result["date"] = result["calm_year"].astype(str) + "-02-01"
    bounded = result["calm_ald_bound_type"].eq("lower")
    result["pf_observed"] = (~bounded).astype(int)
    result["thaw_depth"] = result["calm_ald_cm"].where(~bounded)
    result["pf_depth"] = result["thaw_depth"]
    result["obs_limit"] = result["calm_ald_cm"].where(bounded)
    for kind in ["coordinate", "method"]:
        for field in ["reference", "note"]:
            result[f"calm_{kind}_{field}"] = result["calm_site_code"].map(
                lambda code: overrides.get(code, {}).get(f"{kind}_{field}", "")
            )
    looked_up = result["calm_coordinate_reference"].ne("")
    result["quality_flag_coord_lookup_or_interpolated"] = looked_up
    result["quality_flag_coord_source_flagged"] = looked_up | result["calm_site_code"].eq("SA2C")
    result["quality_flag_source_unit_or_code_recoded"] = looked_up | result["calm_ald_raw"].str.endswith("+")
    result["quality_flag_method_approximate_or_unknown"] = result["calm_method_reference"].ne("") | result["method"].eq("unknown")
    result = result.sort_values(["site_id", "date"], kind="stable").reset_index(drop=True)
    if not (result["lat"].between(-90, 0, inclusive="neither") & result["lon"].between(-180, 180)).all():
        raise ValueError("Invalid Southern Hemisphere coordinates.")
    data_utils.check_columns(result)
    return result, audit


def main() -> None:
    path = HERE / "CALM_S_Summary.xls"
    if hashlib.sha256(path.read_bytes()).hexdigest() != RAW_SHA256:
        raise ValueError("CALM-South raw snapshot changed; review before processing.")
    raw = read_workbook(path)
    overrides = json.loads((HERE / "site_overrides.json").read_text(encoding="utf-8"))["sites"]
    processed, audit = build_processed_table(raw, overrides)
    counts = audit["decision"].value_counts().sort_index().to_dict()
    if len(processed) != 437 or counts.get("zero_unresolved") != 2 or processed["pf_observed"].eq(0).sum() != 11:
        raise ValueError(f"Unexpected CALM-South accounting: {counts}")
    processed.to_csv(HERE / "processed_calm_south.csv", index=False)
    audit.to_csv(HERE / "processing_audit.csv", index=False)
    print(f"CALM_South: {len(processed)} annual observations at {processed.site_id.nunique()} sites; {counts}")


if __name__ == "__main__":
    main()
