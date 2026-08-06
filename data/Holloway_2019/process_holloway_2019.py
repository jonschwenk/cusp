"""
metadata_schema_version = 1
source_key = "Holloway_2019"
release_clearance = "approved"
permission_basis = "published_literature"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-08-04"
source_dataset = '''
Holloway, Jean E.; Lewkowicz, Antoni G. 2020. Half a century of discontinuous
permafrost persistence and degradation in western Canada. Permafrost and
Periglacial Processes 31(1): 85-96. doi:10.1002/ppp.2017
'''
processing_assumptions = [
  "The source workbook is split into 1962 and 2018 observation blocks that are processed separately and concatenated at the end.",
  "For 1962 observations, ALT_cm_1962 is treated as pf_depth and copied to thaw_depth where pf_observed = 1.",
  "For 2017-2018 observations, unmarked ALT values are direct frost-table depths; values marked with * are thermal-gradient estimates for source rows classified as Probable.",
  "Permafrost absence is assigned obs_limit = 200 cm because the paper explicitly defines absence as no directly observed or temperature-gradient-predicted frost table within the upper 2 m.",
  "Question marks and placeholder hyphens are treated as missing values.",
  "method is tp for direct frost-table observations, temp for 2017-2018 probable/absence classifications that use thermal profiles, and tp with a method-approximation flag for the historical 1962 classifications.",
]
temporal_handling = [
  "The September 1962 observations are assigned the representative date 1962-09-15.",
  "The repeat observations span August 2017 and 2018 but cannot be separated row by row in the transcribed table; all are assigned 2018-08-15 and flagged as source-date approximate.",
]
spatial_handling = [
  "Coordinates are read directly from the source workbook without reprojection.",
]
manual_steps = [
  "The source observations were transcribed from a Word-document source into holloway_data.xlsx before this script runs.",
]
known_limitations = [
  "Seven probable repeat-survey frost-table depths and the repeat-survey absence classifications rely on linear extrapolation of instantaneous temperature gradients rather than direct contact with frozen ground.",
  "The repeat-survey table combines observations from 2017 and 2018 without a row-level year field.",
  "The 1962 method is mapped approximately to frost probing from the repeat-study description of Brown's comparable field procedure.",
]
external_dependencies = []
notes = ""
"""
import numpy as np
import pandas as pd

from cusp import data_utils
from cusp.data_utils import _ROOT_DIR


source = "Holloway_2019"
raw = pd.read_excel(_ROOT_DIR / "data" / source / "holloway_data.xlsx")
raw = raw.replace("-", np.nan)

for year in (1962, 2018):
    column = f"olt_cm_{year}"
    raw[f"org_thick_lower_bound_{year}"] = raw[column].astype("string").str.contains(
        ">", na=False
    )
    raw[column] = pd.to_numeric(
        raw[column].astype("string").str.replace(">", "", regex=False).str.strip(),
        errors="coerce",
    )


def common_frame(year):
    """Extract shared source fields for one survey block."""

    return data_utils.csvify_working(
        raw,
        lon_name="Long",
        lat_name="Lat",
        source=source,
        col_tokeep=[
            "site_number",
            f"pf_observed_{year}",
            f"ALT_cm_{year}",
            f"olt_cm_{year}",
            f"org_thick_lower_bound_{year}",
            f"Canopy and Surface {year}",
            "Burn Year",
            "Relief",
            "Soil Type",
        ],
    ).rename(
        columns={
            "site_number": "site_id",
            f"pf_observed_{year}": "pf_observed",
            f"ALT_cm_{year}": "pf_depth",
            f"olt_cm_{year}": "org_thick",
            f"org_thick_lower_bound_{year}": "org_thick_lower_bound",
            f"Canopy and Surface {year}": "Canopy and Surface",
        }
    )


survey_1962 = common_frame(1962)
survey_1962["pf_observed"] = survey_1962["pf_observed"].replace(
    {"Yes": 1, "No": 0}
)
survey_1962["pf_observed"] = pd.to_numeric(
    survey_1962["pf_observed"], errors="coerce"
)
survey_1962 = survey_1962.dropna(subset=["pf_observed"]).copy()
survey_1962["pf_observed"] = survey_1962["pf_observed"].astype(int)
survey_1962["pf_depth"] = pd.to_numeric(
    survey_1962["pf_depth"], errors="coerce"
).where(survey_1962["pf_observed"].eq(1))
survey_1962["thaw_depth"] = survey_1962["pf_depth"]
survey_1962["obs_limit"] = np.where(
    survey_1962["pf_observed"].eq(0), 200.0, np.nan
)
survey_1962["date"] = "1962-09-15"
survey_1962["method"] = "tp"
survey_1962["quality_flag_date_assigned"] = True
survey_1962["quality_flag_method_approximate_or_unknown"] = True
survey_1962["quality_flag_obs_limit_assumed"] = survey_1962[
    "pf_observed"
].eq(0)

survey_2018 = common_frame(2018)
probable = survey_2018["pf_observed"].eq("Probable")
survey_2018["pf_observed"] = survey_2018["pf_observed"].replace(
    {"Probable": 1, "Yes": 1, "No": 0}
)
survey_2018["pf_observed"] = pd.to_numeric(
    survey_2018["pf_observed"], errors="coerce"
)
survey_2018 = survey_2018.dropna(subset=["pf_observed"]).copy()
probable = probable.loc[survey_2018.index]
survey_2018["pf_observed"] = survey_2018["pf_observed"].astype(int)
survey_2018["pf_depth"] = pd.to_numeric(
    survey_2018["pf_depth"]
    .astype("string")
    .str.replace("*", "", regex=False)
    .str.strip(),
    errors="coerce",
).where(survey_2018["pf_observed"].eq(1))
survey_2018["thaw_depth"] = survey_2018["pf_depth"]
absence_2018 = survey_2018["pf_observed"].eq(0)
survey_2018["obs_limit"] = np.where(absence_2018, 200.0, np.nan)
survey_2018["date"] = "2018-08-15"
survey_2018["method"] = np.where(probable | absence_2018, "temp", "tp")
survey_2018["quality_flag_date_assigned"] = True
survey_2018["quality_flag_date_source_approximate"] = True
survey_2018["quality_flag_obs_limit_assumed"] = absence_2018
survey_2018["quality_flag_model_or_estimate"] = probable | absence_2018

df = pd.concat([survey_2018, survey_1962], ignore_index=True)
df["quality_flag_upper_bound_presence"] = (
    df["pf_observed"].eq(1) & df["pf_depth"].isna()
)
data_utils.check_columns(df)
df.to_csv(
    _ROOT_DIR / "data" / source / f"processed_{source.lower()}.csv", index=False
)
