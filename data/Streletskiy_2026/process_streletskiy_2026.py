"""
metadata_schema_version = 1
source_key = "Streletskiy_2026"
release_clearance = "approved"
permission_basis = "public_repository_terms"
original_author = "jschwenk + Codex"
last_substantive_update = "2026-10-05"
source_dataset = '''
Streletskiy, Dmitry (2026): CALM sites locations and climatic conditions
extracted from ERA5-Land with long-term ALT annual data (2000-2024).
Figshare, version 1. https://doi.org/10.6084/m9.figshare.32885756.v1
CALM_Sites_Data.csv, file id 66270764, retrieved 2026-10-05.
Related paper: https://doi.org/10.1038/s43247-026-03824-1
'''
processing_assumptions = [
  "Only annual observed ALT in cm is ingested, not ERA5-Land climate estimates, trends, significance tests, or derived climate metrics. Positive exact ALT implies presence with pf_depth = thaw_depth = ALT.",
  "The 3500 site-year rows contain 801 missing/dash ALT entries and two ambiguous zeros. These are excluded, never interpreted as absence.",
  "Normalize whitespace/case in CALM SiteCode and match annual source labels, not placeholder calendar dates. For all 2212 positive rows already represented by CALM, retain existing PANGAEA-derived CALM observations. Audit depth agreement and conflicts: synthesis values must not overwrite bounds, change methods, or silently revise prior observations.",
  "All 270 positive Southern Hemisphere rows are excluded in favor of original CALM_South annual summaries. Assert that each is represented there with the same site/year and depth agreement within 1 cm; this source does not depend on an ambiguous coordinate-only match.",
  "Compare Northern Hemisphere candidates against retained PERMOS calm_id/year records as well; no additional matches occur in the frozen snapshot. Defer CH1 2022 explicitly because the original PERMOS borehole record is unreliable and the replacement borehole is a different observation; review_exclusions.json preserves evidence.",
  "Retain 214 new Northern Hemisphere site-years at 24 sites, with no temporal thinning. These are annual summaries, not dense raw time series. Independent nearby Jorgenson_Kanevskiy_2025 soil-pit measurements are retained, not treated as copies of annual borehole ALT.",
  "METHOD_PLAIN maps Probing to tp, Borehole to temp, and Thaw Tube to tt. This site-level classification may differ from year-specific instruments; flag method_approximate_or_unknown and preserve both method labels.",
]
temporal_handling = [
  "Encode year-only Northern Hemisphere annual observations as September 1, consistent with existing CALM. Retain source year and flag date_assigned; the day is not an actual measurement date.",
]
spatial_handling = [
  "Use the versioned CSV's latitude/longitude as representative WGS84 site coordinates; preserve site names and country/region fields. No grid-node locations or spatial thinning are invented.",
]
manual_steps = [
  "Download file 66270764 and Figshare article metadata from https://api.figshare.com/v2/articles/32885756; preserve the version-1 raw CSV and metadata snapshot unchanged.",
]
known_limitations = [
  "This is a republished synthesis, not the original producer of every observation. Cite the versioned extract and retain provider references in the related paper; do not relabel these records as original CALM/PERMOS exports. Contact-only native files are not a prerequisite to ingesting the accessible synthesis observations.",
  "Same-CALM-site/year disagreements are deferred, not resolved scientifically by the filter. Existing richer source provenance and bounded values take precedence; the audit preserves conflicting candidate values and methods.",
  "One Swiss annual value and two zeros remain unresolved. Finer-scale provider data remain optional follow-up leads in separate dataset issues linked from the source README, not prerequisites to the finalized annual ingestion under issue #36.",
]
external_dependencies = [
  "data/CALM/processed_calm.csv, data/CALM_South/processed_calm_south.csv, and data/PERMOS_2024/processed_permos_2024.csv are required for source-specific deduplication; no network is needed to rerun.",
]
notes = "Figshare version 1 is CC BY 4.0. Maintainer explicitly authorized finalization into CUSP on 2026-10-05, including using accessible synthesis observations when native provider files are contact-only. Existing downloadable CALM, CALM-South, and PERMOS tables remain required reproducible deduplication inputs; no author contact is needed. No new CUSP release is published by this approval."
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from cusp import data_utils

HERE = Path(__file__).resolve().parent
RAW_SHA256 = "6794f7db24f0f868bea17724bdcd2c8beb6b66fd2f58f5a803eca45426887f46"
METHODS = {"Probing": "tp", "Borehole": "temp", "Thaw Tube": "tt"}


def normalized_codes(values: pd.Series) -> pd.Series:
    return values.astype("string").str.replace(r"\s+", "", regex=True).str.upper()


def coverage_table(frame: pd.DataFrame, code: str, year: str) -> pd.DataFrame:
    result = pd.DataFrame({
        "code": normalized_codes(frame[code]),
        "year": pd.to_numeric(frame[year], errors="raise").astype("Int64"),
        "depth": pd.to_numeric(frame["thaw_depth"], errors="raise"),
        "method": frame["method"],
        "pf_observed": frame["pf_observed"],
        "obs_limit": frame["obs_limit"],
    }).dropna(subset=["code", "year"])
    if result.duplicated(["code", "year"]).any():
        raise ValueError("Ambiguous provider site/year coverage; review independent measurements.")
    return result.set_index(["code", "year"])


def build_processed_table(
    raw: pd.DataFrame,
    calm: pd.DataFrame,
    south: pd.DataFrame,
    permos: pd.DataFrame,
    exclusions: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    audit = raw.copy().reset_index(drop=True)
    audit["calm_site_code"] = normalized_codes(audit["SiteCode"])
    audit["calm_year"] = pd.to_numeric(audit["year"], errors="raise").astype(int)
    if audit["calm_site_code"].isna().any() or audit["calm_site_code"].eq("").any():
        raise ValueError("Missing CALM site codes.")
    if audit.duplicated(["calm_site_code", "calm_year"]).any():
        raise ValueError("Duplicate synthesis site/year; review rather than dropping observations.")
    audit["calm_ald_raw"] = audit["ALT"]
    text = audit["ALT"].astype("string").str.strip()
    audit["alt_cm"] = pd.to_numeric(text, errors="coerce")
    invalid = audit["alt_cm"].isna() & text.notna() & ~text.isin(["", "-"])
    if invalid.any() or audit["alt_cm"].lt(0).any():
        raise ValueError("Unexpected synthesis ALT encoding; bounds must not be flattened.")
    if not (audit["Lat"].between(-90, 90) & audit["Lon"].between(-180, 180)).all():
        raise ValueError("Invalid synthesis coordinates.")
    if not audit["METHOD_PLAIN"].isin(METHODS).all():
        raise ValueError("Unrecognized synthesis method labels.")
    calm_keys = coverage_table(calm, "calm_site_code", "calm_year")
    south_keys = coverage_table(south, "calm_site_code", "calm_year")
    permos_codes = normalized_codes(permos["permos_calm_id"])
    permos_coverage = pd.DataFrame({
        "code": permos_codes,
        "year": pd.to_numeric(permos["permos_year"], errors="raise").astype("Int64"),
    }).dropna(subset=["code", "year"])
    if permos_coverage.duplicated(["code", "year"]).any():
        raise ValueError("Ambiguous PERMOS site/year coverage; review independent measurements.")
    permos_keys = set(zip(permos_coverage["code"], permos_coverage["year"], strict=True))
    decisions = []
    provider_depths = []
    provider_methods = []
    provider_states = []
    provider_limits = []
    for row in audit.itertuples(index=False):
        key = (row.calm_site_code, row.calm_year)
        provider = None
        if pd.isna(row.alt_cm):
            reason = "missing_alt"
        elif row.alt_cm == 0:
            reason = "zero_unresolved"
        elif row.Lat < 0:
            if key not in south_keys.index:
                raise ValueError(f"Southern synthesis observation is not represented by CALM_South: {key}")
            provider = south_keys.loc[key]
            if pd.isna(provider["depth"]) or abs(provider["depth"] - row.alt_cm) > 1.0:
                raise ValueError(f"Southern provider depth conflict: {key}")
            reason = "original_calm_south_retained"
        elif key in calm_keys.index:
            provider = calm_keys.loc[key]
            if pd.isna(provider["depth"]):
                reason = "calm_bound_or_nonexact_retained"
            elif abs(provider["depth"] - row.alt_cm) <= 1.0:
                reason = "calm_republication_retained"
            else:
                reason = "calm_conflict_deferred"
        elif f"{key[0]}:{key[1]}" in exclusions:
            reason = exclusions[f"{key[0]}:{key[1]}"]["reason"]
        elif key in permos_keys:
            reason = "original_permos_retained"
        else:
            reason = "retained"
        decisions.append(reason)
        provider_depths.append(provider["depth"] if provider is not None else np.nan)
        provider_methods.append(provider["method"] if provider is not None else "")
        provider_states.append(provider["pf_observed"] if provider is not None else np.nan)
        provider_limits.append(provider["obs_limit"] if provider is not None else np.nan)
    audit["decision"] = decisions
    audit["retained_provider_depth_cm"] = provider_depths
    audit["retained_provider_method"] = provider_methods
    audit["retained_provider_pf_observed"] = provider_states
    audit["retained_provider_obs_limit_cm"] = provider_limits
    audit["review_reference"] = [exclusions.get(f"{code}:{year}", {}).get("reference", "") for code, year in zip(audit.calm_site_code, audit.calm_year, strict=True)]
    result = audit.loc[audit["decision"].eq("retained")].copy()
    result["site_id"] = "CALM_" + result["calm_site_code"]
    result["source"] = "Streletskiy_2026"
    result["lat"] = result["Lat"]
    result["lon"] = result["Lon"]
    result["date"] = result["calm_year"].astype(str) + "-09-01"
    result["pf_observed"] = 1
    result["thaw_depth"] = result["alt_cm"]
    result["pf_depth"] = result["alt_cm"]
    result["obs_limit"] = np.nan
    result["method"] = result["METHOD_PLAIN"].map(METHODS)
    # Retain observational provenance, not unrelated climate/model output fields.
    provenance = ["ID", "Site_Name", "SiteCode", "Country", "Region", "Elevation", "METHOD", "METHOD_PLAIN", "calm_site_code", "calm_year", "calm_ald_raw"]
    canonical = ["site_id", "source", "date", "lat", "lon", "pf_observed", "pf_depth", "thaw_depth", "obs_limit", "method"]
    result = result.loc[:, canonical + provenance].sort_values(["site_id", "date"], kind="stable").reset_index(drop=True)
    data_utils.check_columns(result)
    return result, audit


def main() -> None:
    path = HERE / "CALM_Sites_Data.csv"
    if hashlib.sha256(path.read_bytes()).hexdigest() != RAW_SHA256:
        raise ValueError("Figshare version-1 snapshot changed; review before processing.")
    metadata = json.loads((HERE / "figshare_metadata.json").read_text(encoding="utf-8"))
    if metadata["version"] != 1 or metadata["license"]["name"] != "CC BY 4.0":
        raise ValueError("Unexpected Figshare version/license.")
    provider_paths = {
        "calm": ROOT / "data/CALM/processed_calm.csv",
        "south": ROOT / "data/CALM_South/processed_calm_south.csv",
        "permos": ROOT / "data/PERMOS_2024/processed_permos_2024.csv",
    }
    for provider_path in provider_paths.values():
        if not provider_path.exists():
            raise FileNotFoundError(f"{provider_path} is required for synthesis overlap filtering.")
    providers = {key: pd.read_csv(value, low_memory=False) for key, value in provider_paths.items()}
    exclusions = json.loads((HERE / "review_exclusions.json").read_text(encoding="utf-8"))
    processed, audit = build_processed_table(pd.read_csv(path, low_memory=False), **providers, exclusions=exclusions)
    counts = audit["decision"].value_counts().sort_index().to_dict()
    if len(audit) != 3500 or len(processed) != 214 or counts.get("original_calm_south_retained") != 270 or sum(count for reason, count in counts.items() if reason.startswith("calm_")) != 2212 or counts.get("unresolved_permos_quality_conflict") != 1:
        raise ValueError(f"Unexpected synthesis accounting: {counts}")
    processed.to_csv(HERE / "processed_streletskiy_2026.csv", index=False)
    audit.to_csv(HERE / "processing_audit.csv", index=False)
    print(f"Streletskiy_2026: {len(processed)} annual observations at {processed.site_id.nunique()} sites; {counts}")


if __name__ == "__main__":
    main()
