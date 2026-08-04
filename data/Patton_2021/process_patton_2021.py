"""
metadata_schema_version = 1
source_key = "Patton_2021"
release_clearance = "approved"
permission_basis = "published_literature"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-04"
source_dataset = '''
Patton, A. I.; Rathburn, S. L.; Capps, D. M.; McGrath, D.; Brown, R. A. 2021.
Ongoing landslide deformation in thawing permafrost. Geophysical Research
Letters 48, e2021GL092959. https://doi.org/10.1029/2021GL092959
'''
processing_assumptions = [
  "Three GPR transects are processed separately and then concatenated into one output table.",
  "alt_m is converted from meters to centimeters.",
  "Native dense GPR picks are aggregated to one mean observation per occupied 5 m by 5 m UTM cell within transect and survey date.",
  "Every retained numeric GPR active-layer depth is treated as a permafrost detection at the reported interpreted depth; no arbitrary 130 cm threshold is applied.",
  "method is set to gp and pf_depth is copied from thaw_depth.",
]
temporal_handling = [
  "Each transect is assigned a fixed survey date hardcoded in the script.",
]
spatial_handling = [
  "Transect coordinates are interpreted in EPSG:6334 and transformed to WGS84.",
  "GPR aggregation uses a local UTM projection selected independently for each transect/date survey unit.",
]
manual_steps = []
known_limitations = [
  "The script assumes NAD83(2011) and WGS84 are close enough for this application, which the original author flagged as an unresolved source of roughly meter-scale horizontal error.",
  "Permafrost depths are geophysical interpretations rather than mechanical probe contacts.",
  "A 2026-08-04 cross-source footprint and coordinate/depth/date audit found no overlap with the retained Jafarov_2016, Moore_et_al_2025, or Petrone_etal_2016 GPR observations, so no cross-source rows are removed here.",
]
external_dependencies = []
notes = ""
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

from cusp import data_utils
from cusp.data_utils import _ROOT_DIR


SOURCE = "Patton_2021"
SOURCE_DIR = _ROOT_DIR / "data" / SOURCE

TRANSECTS = [
    ("GPR/SP_LINE0202_picks.csv", "\t", "sp_line01", "2018-08-14"),
    ("GPR/SP_LINE0302_picks.csv", ",", "sp_line02", "2018-08-15"),
    ("GPR/PT_LINE0403_picks.csv", "\t", "pt_line03", "2018-08-16"),
]


def load_transect(relative_path: str, delimiter: str, site_id: str, date: str) -> pd.DataFrame:
    """Load one native GPR pick table and convert its coordinates to WGS84."""

    raw = pd.read_csv(SOURCE_DIR / relative_path, delimiter=delimiter)
    for column in ["easting_m", "northing_m", "alt_m"]:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
    raw = raw.dropna(subset=["easting_m", "northing_m", "alt_m"]).copy()

    points = gpd.GeoDataFrame(
        raw,
        geometry=gpd.points_from_xy(raw["easting_m"], raw["northing_m"]),
        crs="EPSG:6334",
    ).to_crs("EPSG:4326")
    return pd.DataFrame(
        {
            "site_id": site_id,
            "date": date,
            "lat": points.geometry.y,
            "lon": points.geometry.x,
            "thaw_depth": points["alt_m"] * 100.0,
            "method": "gp",
            "source": SOURCE,
            "quality_flag_pf_state_assumed": True,
        }
    )


def build_observations() -> pd.DataFrame:
    native = pd.concat(
        [load_transect(*specification) for specification in TRANSECTS],
        ignore_index=True,
    )
    out = data_utils.aggregate_gpr_points(native, spacing_m=5.0)
    out["pf_observed"] = pd.Series(1, index=out.index, dtype="Int64")
    out["pf_depth"] = out["thaw_depth"]
    out["obs_limit"] = np.nan
    return out


def main() -> None:
    out = build_observations()
    data_utils.check_columns(out)
    output_path = SOURCE_DIR / f"processed_{SOURCE.lower()}.csv"
    out.to_csv(output_path, index=False)
    print(
        f"Wrote {len(out):,} aggregated GPR rows to {output_path} "
        f"from {int(out['gpr_native_count'].sum()):,} native picks."
    )


if __name__ == "__main__":
    main()
