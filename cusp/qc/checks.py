from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from .reporting import CORE_ID_COLS, DEPTH_COLS, safe_cols


DEFAULT_TOO_OLD_YEAR = 1900
DEFAULT_FUTURE_YEAR_BUFFER = 1


@dataclass
class CheckResult:
    mask: pd.Series
    details: pd.DataFrame
    stats: dict[str, Any] | None = None

    def count(self) -> int:
        return int(self.mask.sum())


def _empty_mask(df: pd.DataFrame) -> pd.Series:
    return pd.Series(False, index=df.index, dtype=bool)


def _empty_details(cols: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=cols)


def _build_details(
    df: pd.DataFrame,
    mask: pd.Series,
    base_cols: list[str],
    extra_cols: dict[str, pd.Series],
) -> pd.DataFrame:
    base = df.loc[mask, safe_cols(df, base_cols)].copy()
    for name, series in extra_cols.items():
        base[name] = series.loc[base.index]
    cols = safe_cols(df, base_cols) + list(extra_cols.keys())
    base = base.reindex(columns=cols)
    if base.empty:
        base = pd.DataFrame(columns=cols)
    return base


def check_cusp_obs_id(df: pd.DataFrame) -> CheckResult:
    """Ensure observation IDs are present and unique."""

    base_cols = CORE_ID_COLS
    if "cusp_obs_id" not in df.columns:
        missing = pd.Series(True, index=df.index, dtype=bool)
        return CheckResult(
            mask=missing,
            details=_build_details(df, missing, base_cols, {"flag_missing_cusp_obs_id": missing}),
            stats={"n_missing_cusp_obs_id": int(missing.sum()), "n_duplicate_cusp_obs_id": 0},
        )

    missing = df["cusp_obs_id"].isna() | (df["cusp_obs_id"].astype("string").str.strip() == "")
    duplicate = df["cusp_obs_id"].duplicated(keep=False) & ~missing
    mask = missing | duplicate

    details = _build_details(
        df,
        mask,
        base_cols,
        {
            "flag_missing_cusp_obs_id": missing,
            "flag_duplicate_cusp_obs_id": duplicate,
        },
    )

    stats = {
        "n_missing_cusp_obs_id": int(missing.sum()),
        "n_duplicate_cusp_obs_id": int(duplicate.sum()),
    }
    return CheckResult(mask=mask, details=details, stats=stats)


def check_dates(
    df: pd.DataFrame,
    too_old_year: int = DEFAULT_TOO_OLD_YEAR,
    future_year_buffer: int = DEFAULT_FUTURE_YEAR_BUFFER,
) -> CheckResult:
    """Flag missing, unparseable, too-old, or future dates."""

    if "date" in df.columns:
        dt = pd.to_datetime(df["date"], errors="coerce")
    else:
        dt = pd.Series(pd.NaT, index=df.index)

    year = dt.dt.year
    cutoff_future_year = datetime.now(timezone.utc).year + future_year_buffer

    bad_unparseable = dt.isna()
    bad_future = year > cutoff_future_year
    bad_too_old = year < too_old_year
    mask = bad_unparseable | bad_future | bad_too_old

    details = _build_details(
        df,
        mask,
        CORE_ID_COLS,
        {
            "date_parsed": dt.astype("string"),
            "year_parsed": year,
            "flag_unparseable": bad_unparseable,
            "flag_future": bad_future,
            "flag_too_old": bad_too_old,
        },
    )

    stats = {
        "n_date_unparseable": int(bad_unparseable.sum()),
        "n_date_future": int(bad_future.sum()),
        "n_date_too_old": int(bad_too_old.sum()),
        "cutoff_future_year": cutoff_future_year,
        "too_old_year": too_old_year,
    }
    return CheckResult(mask=mask, details=details, stats=stats)


def check_coordinates(df: pd.DataFrame) -> CheckResult:
    """Flag missing or out-of-range coordinates."""

    have_xy = {"lat", "lon"}.issubset(df.columns)
    if have_xy:
        lat = pd.to_numeric(df["lat"], errors="coerce")
        lon = pd.to_numeric(df["lon"], errors="coerce")
        missing_xy = lat.isna() | lon.isna()
        invalid_range = (lat < -90) | (lat > 90) | (lon < -180) | (lon > 180)
    else:
        missing_xy = pd.Series(True, index=df.index, dtype=bool)
        invalid_range = pd.Series(False, index=df.index, dtype=bool)

    mask = missing_xy | invalid_range
    details = _build_details(
        df,
        mask,
        CORE_ID_COLS,
        {
            "flag_missing_xy": missing_xy,
            "flag_invalid_range": invalid_range,
        },
    )
    stats = {
        "n_missing_xy": int(missing_xy.sum()),
        "n_invalid_xy_range": int(invalid_range.sum()),
    }
    return CheckResult(mask=mask, details=details, stats=stats)


def check_negative_depths(df: pd.DataFrame) -> CheckResult:
    """Flag negative depth values."""

    neg_pf = (
        pd.to_numeric(df["pf_depth"], errors="coerce") < 0
        if "pf_depth" in df.columns
        else _empty_mask(df)
    )
    neg_thaw = (
        pd.to_numeric(df["thaw_depth"], errors="coerce") < 0
        if "thaw_depth" in df.columns
        else _empty_mask(df)
    )
    neg_obs_limit = (
        pd.to_numeric(df["obs_limit"], errors="coerce") < 0
        if "obs_limit" in df.columns
        else _empty_mask(df)
    )
    mask = neg_pf | neg_thaw | neg_obs_limit

    details = _build_details(
        df,
        mask,
        CORE_ID_COLS + DEPTH_COLS,
        {
            "flag_negative_pf_depth": neg_pf,
            "flag_negative_thaw_depth": neg_thaw,
            "flag_negative_obs_limit": neg_obs_limit,
        },
    )
    stats = {
        "n_negative_pf_depth": int(neg_pf.sum()),
        "n_negative_thaw_depth": int(neg_thaw.sum()),
        "n_negative_obs_limit": int(neg_obs_limit.sum()),
    }
    return CheckResult(mask=mask, details=details, stats=stats)


def check_zero_obs_limit(df: pd.DataFrame) -> CheckResult:
    """Flag zero observation limits, which should be resolved upstream."""

    base_cols = CORE_ID_COLS + DEPTH_COLS + ["pf_observed"]
    if "obs_limit" not in df.columns:
        return CheckResult(mask=_empty_mask(df), details=_empty_details(base_cols), stats=None)

    obs_limit = pd.to_numeric(df["obs_limit"], errors="coerce")
    mask = obs_limit == 0
    details = _build_details(df, mask, base_cols, {})
    stats = {"n_zero_obs_limit": int(mask.sum())}
    return CheckResult(mask=mask, details=details, stats=stats)


def check_pf_observed_values(df: pd.DataFrame) -> CheckResult:
    """Flag non-null pf_observed values outside {0, 1}."""

    base_cols = CORE_ID_COLS + ["pf_observed"]
    if "pf_observed" not in df.columns:
        return CheckResult(mask=_empty_mask(df), details=_empty_details(base_cols), stats=None)

    raw = df["pf_observed"]
    numeric = pd.to_numeric(raw, errors="coerce")
    bad = raw.notna() & ~numeric.isin([0, 1])

    details = _build_details(df, bad, base_cols, {})
    stats = {"n_invalid_pf_observed": int(bad.sum())}
    return CheckResult(mask=bad, details=details, stats=stats)


def check_method_values(df: pd.DataFrame, allowed_methods: set[str]) -> CheckResult:
    """Flag missing or unsupported observation method values."""

    base_cols = CORE_ID_COLS
    if "method" not in df.columns:
        missing = pd.Series(True, index=df.index, dtype=bool)
        return CheckResult(
            mask=missing,
            details=_build_details(df, missing, base_cols, {"flag_missing_method": missing}),
            stats={"n_missing_method": int(missing.sum()), "n_unsupported_method": 0},
        )

    method = df["method"].astype("string").str.strip()
    missing = method.isna() | (method == "")
    unsupported = ~missing & ~method.isin(sorted(allowed_methods))
    mask = missing | unsupported
    details = _build_details(
        df,
        mask,
        base_cols,
        {
            "flag_missing_method": missing,
            "flag_unsupported_method": unsupported,
        },
    )
    stats = {
        "n_missing_method": int(missing.sum()),
        "n_unsupported_method": int(unsupported.sum()),
    }
    return CheckResult(mask=mask, details=details, stats=stats)


def check_thaw_depth_gt_pf_depth(df: pd.DataFrame) -> CheckResult:
    """Diagnostic: thaw depth deeper than pf_depth."""

    base_cols = CORE_ID_COLS + ["pf_depth", "thaw_depth", "obs_limit", "delta_thaw_minus_pf"]
    if not {"thaw_depth", "pf_depth"}.issubset(df.columns):
        return CheckResult(mask=_empty_mask(df), details=_empty_details(base_cols), stats=None)

    thaw_depth = pd.to_numeric(df["thaw_depth"], errors="coerce")
    pf_depth = pd.to_numeric(df["pf_depth"], errors="coerce")
    mask = thaw_depth.notna() & pf_depth.notna() & (thaw_depth > pf_depth)

    details = _build_details(
        df,
        mask,
        CORE_ID_COLS + ["pf_depth", "thaw_depth", "obs_limit"],
        {"delta_thaw_minus_pf": thaw_depth - pf_depth},
    )
    stats = {"n_thaw_gt_pf": int(mask.sum())}
    return CheckResult(mask=mask, details=details, stats=stats)


def check_suspect_swapped_latlon(df: pd.DataFrame) -> CheckResult:
    """Diagnostic: coarse heuristic for swapped latitude/longitude pairs."""

    base_cols = CORE_ID_COLS + DEPTH_COLS + ["pf_observed"]
    if not {"lat", "lon"}.issubset(df.columns):
        return CheckResult(mask=_empty_mask(df), details=_empty_details(base_cols), stats=None)

    lat = pd.to_numeric(df["lat"], errors="coerce")
    lon = pd.to_numeric(df["lon"], errors="coerce")
    have = lat.notna() & lon.notna()

    lat_looks_like_lon = have & lat.between(-180, -120)
    lon_looks_like_lat = have & lon.between(50, 80)
    mask = lat_looks_like_lon & lon_looks_like_lat

    details = _build_details(df, mask, base_cols, {})
    stats = {"n_suspect_swapped_latlon": int(mask.sum())}
    return CheckResult(mask=mask, details=details, stats=stats)
