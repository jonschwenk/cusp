"""
metadata_schema_version = 1
source_key = "Seward"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-04"
source_dataset = '''
Thaler, E.; Uhlemann, S.; Rowland, J.; Dafflon, B.; Schwenk, J.; Bennett, K.;
Thomas, L. 2023. Machine learning predictions of near-surface permafrost extent
at Teller 27, Teller 47, and the Kougarok 64 Hillslope sites on the Seward
Peninsula, Alaska: Supporting Data. NGEE Arctic / ESS-DIVE.
doi:10.5440/1970774

Thaler, E. A. et al. 2023. High-Resolution Maps of Near-Surface Permafrost for
Three Watersheds on the Seward Peninsula, Alaska Derived From Machine Learning.
Earth and Space Science 10, e2023EA003015. doi:10.1029/2023EA003015
'''
processing_assumptions = [
  "Three ground-truth tables (KG, T47, and T27) are processed separately and concatenated.",
  "Only source presence/absence classifications are retained; the source tables do not provide row-level thaw or permafrost depth.",
  "Permafrost absence is represented to a conservative 100 cm observation limit, matching the study's near-surface permafrost definition and remaining within the 0.75-1.20 m range of manual temperature observations.",
  "The tables combine classifications from co-located ERT and temperature measurements with manual temperature profiles, frost probing, trenches, and exposed-bedrock observations; row-level method provenance is unavailable, so method is unknown.",
]
temporal_handling = [
  "KG is assigned 2019-08-15 from its 2019 late-summer survey year.",
  "T27 is assigned 2018-08-15, the earliest primary survey year, but the source table also includes 2022 observations that cannot be identified row by row.",
  "T47 is assigned 2021-09-15, the primary geophysical survey year, but the source table also includes manual observations from August 2022 that cannot be identified row by row.",
]
spatial_handling = [
  "Source X/Y coordinates are interpreted in EPSG:32603 and reprojected to WGS84 before export.",
]
manual_steps = []
known_limitations = [
  "T27 and T47 are multi-year composite tables without row-level dates; their assigned dates must not be interpreted as exact observation dates.",
  "The exact observation method cannot be recovered for individual rows from the released ground-truth tables.",
  "The 100 cm absence limit is a conservative source-level interpretation rather than a row-specific measured limit.",
]
external_dependencies = []
notes = ""
"""
import numpy as np
import pandas as pd

from cusp import data_utils
from cusp.data_utils import _ROOT_DIR

source = "Seward"


def process_site(filename, site_id, representative_date, campaign_years):
    """Normalize one source ground-truth table."""

    raw = pd.read_csv(_ROOT_DIR / "data" / source / filename)
    raw = raw.rename(columns={"PF": "pf_observed"})
    raw["date"] = representative_date

    gdf = data_utils.geoify_working(
        raw.copy(),
        crs="EPSG:32603",
        lat_name="Y",
        lon_name="X",
        col_tokeep=["pf_observed", "date"],
    ).to_crs(epsg=4326)

    out = pd.DataFrame(gdf.drop(columns="geometry"))
    out["lon"] = [geometry.x for geometry in gdf.geometry]
    out["lat"] = [geometry.y for geometry in gdf.geometry]
    out["site_id"] = site_id
    out["source_campaign_years"] = campaign_years
    out["pf_observed"] = pd.to_numeric(
        out["pf_observed"], errors="raise"
    ).astype(int)
    out["pf_depth"] = np.nan
    out["thaw_depth"] = np.nan
    out["obs_limit"] = np.where(out["pf_observed"].eq(0), 100.0, np.nan)
    out["method"] = "unknown"
    out["quality_flag_date_assigned"] = True
    out["quality_flag_date_source_approximate"] = ";" in campaign_years
    out["quality_flag_obs_limit_assumed"] = out["pf_observed"].eq(0)
    out["quality_flag_upper_bound_presence"] = out["pf_observed"].eq(1)
    return out


kg = process_site("KG_points.csv", "KG", "2019-08-15", "2019")
t47 = process_site(
    "T47CombinedTrainingData.csv", "T47", "2021-09-15", "2021;2022"
)
t27 = process_site(
    "Teller27_points_trimmed.csv", "T27", "2018-08-15", "2018;2022"
)

df = pd.concat([kg, t47, t27], ignore_index=True)
df["source"] = source

data_utils.check_columns(df)
df.to_csv(
    _ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False
)
