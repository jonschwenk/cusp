"""
metadata_schema_version = 1
source_key = "Bonnaventure_Whati"
release_clearance = "approved"
permission_basis = "emailed_approval"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-04"
source_dataset = '''
Ground-truth cryotic-assessment points collected around Whati, Northwest
Territories, in August 2019 and shared by Philip P. Bonnaventure for CUSP.
The observations are described by Daly, Bonnaventure, and Kochtitzky (2022),
doi:10.1002/ppp.2160, and reused by Bonnaventure et al. (2026),
doi:10.1002/ppp.70037. The 2026 paper does not distribute the point file and
instead directs readers to contact the authors for data access.
'''
processing_assumptions = [
  "The source PF field is carried directly into pf_observed after coordinate and column normalization.",
  "Permafrost-absence rows are assigned obs_limit = 150 cm from the study's conservative cryotic-assessment protocol target; this is not a row-specific measured depth.",
  "The field protocol used soil probes or hammer-drill pilot holes followed by bottom-hole temperature profiles, so method is mapped to temp for the final permafrost classification.",
  "Presence rows have no released frost-table depth and are retained as upper-bounded presence observations.",
  "The available CSV does not identify the 31 published sites whose state used thermal-gradient extrapolation, so model_or_estimate is conservatively attached to every row from this source.",
]
temporal_handling = [
  "All observations are assigned 2019-08-15, the midpoint of the reported August 2019 field campaign, and receive assigned/approximate-date flags.",
]
spatial_handling = [
  "X and Y are interpreted as WGS84 longitude and latitude; the original waypoint Name is retained as site_id.",
  "The study reports GPS waypoint averaging with approximately 1-4 m positional accuracy.",
]
manual_steps = [
  "The groundTruthLocs.csv file was supplied directly by Philip P. Bonnaventure under emailed permission; CUSP treats it as the field dataset used by the linked publications rather than as a file distributed with either paper.",
]
known_limitations = [
  "The directly shared file is believed to contain the ground-truth observations used in the linked publications, but row-for-row identity cannot be verified from public supplements because the papers do not distribute the point file.",
  "The shared file contains 145 unique points (83 presence and 62 absence), six more absence points than the 139 sites reported in Daly et al. (2022) and Bonnaventure et al. (2026). The row-level reason for that difference is not available.",
  "The shared file omits pilot-hole depth, temperature-gradient classification, and observation-tool fields, so those distinctions cannot be recovered per row.",
  "The assigned 150 cm absence limit is conservative but may differ from actual hole depths, reported in the study as approximately 30-189 cm.",
]
external_dependencies = []
notes = "The source key and directory use the corrected spelling Bonnaventure."
"""

import numpy as np
import pandas as pd

from cusp import data_utils
from cusp.data_utils import _ROOT_DIR


source = "Bonnaventure_Whati"
source_dir = _ROOT_DIR / "data" / source

raw = pd.read_csv(source_dir / "groundTruthLocs.csv", na_values=[-9999])
expected_columns = {"Name", "Type", "PF", "X", "Y"}
missing_columns = expected_columns.difference(raw.columns)
if missing_columns:
    raise ValueError(f"Bonnaventure source is missing columns: {sorted(missing_columns)}")

df = data_utils.csvify_working(
    raw.loc[:, ["Name", "Type", "PF", "X", "Y"]].copy(),
    lat_name="Y",
    lon_name="X",
    source=source,
    col_tokeep=["Name", "Type", "PF"],
).rename(
    columns={
        "Name": "site_id",
        "Type": "bonnaventure_point_type",
        "PF": "pf_observed",
    }
)

df["pf_observed"] = pd.to_numeric(df["pf_observed"], errors="raise").astype(int)
if len(df) != 145 or df["pf_observed"].value_counts().to_dict() != {1: 83, 0: 62}:
    raise ValueError("Unexpected Bonnaventure row count or permafrost-state counts.")

absence = df["pf_observed"].eq(0)
presence = df["pf_observed"].eq(1)
df["date"] = "2019-08-15"
df["pf_depth"] = np.nan
df["thaw_depth"] = np.nan
df["obs_limit"] = np.where(absence, 150.0, np.nan)
df["method"] = "temp"
df["bonnaventure_published_site_count"] = 139
df["bonnaventure_shared_site_count"] = 145
df["bonnaventure_protocol_limit_cm"] = 150.0

df["quality_flag_obs_limit_assumed"] = absence
df["quality_flag_upper_bound_presence"] = presence
df["quality_flag_date_assigned"] = True
df["quality_flag_date_source_approximate"] = True
df["quality_flag_model_or_estimate"] = True

data_utils.check_columns(df)
df.to_csv(source_dir / f"processed_{source.lower()}.csv", index=False)
