"""Aggregation-specific QA helpers for release-facing artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


AGGREGATED_COLUMNS = [
    "cusp_30m_id",
    "year",
    "date",
    "lat",
    "lon",
    "pf_observed",
    "thaw_depth",
    "pf_depth",
    "obs_limit",
    "method",
    "aggregated_sources",
    "n_grouped",
]


@dataclass
class AggregateCheckResult:
    mask: pd.Series
    details: pd.DataFrame
    stats: dict[str, Any] | None = None

    def count(self) -> int:
        return int(self.mask.sum())


def load_aggregated_csv(path: str) -> pd.DataFrame:
    """Load the canonical 30 m aggregation with a stable row index."""

    df = pd.read_csv(path, low_memory=False)
    df.insert(0, "row_index", df.index)
    return df


def check_cusp_30m_id(df: pd.DataFrame) -> AggregateCheckResult:
    """Ensure aggregated IDs are present and unique."""

    missing = df["cusp_30m_id"].isna() | (df["cusp_30m_id"].astype("string").str.strip() == "")
    duplicate = df["cusp_30m_id"].duplicated(keep=False) & ~missing
    mask = missing | duplicate
    details = df.loc[mask, ["row_index", "cusp_30m_id", "year", "date", "lat", "lon"]].copy()
    details["flag_missing_cusp_30m_id"] = missing.loc[details.index]
    details["flag_duplicate_cusp_30m_id"] = duplicate.loc[details.index]
    return AggregateCheckResult(
        mask=mask,
        details=details,
        stats={
            "n_missing_cusp_30m_id": int(missing.sum()),
            "n_duplicate_cusp_30m_id": int(duplicate.sum()),
        },
    )


def check_pf_observed_fraction(df: pd.DataFrame) -> AggregateCheckResult:
    """Ensure aggregated pf_observed stays within [0, 1]."""

    values = pd.to_numeric(df["pf_observed"], errors="coerce")
    mask = values.isna() | (values < 0) | (values > 1)
    details = df.loc[mask, ["row_index", "cusp_30m_id", "pf_observed", "year", "date"]].copy()
    return AggregateCheckResult(
        mask=mask,
        details=details,
        stats={"n_invalid_pf_observed_fraction": int(mask.sum())},
    )


def check_n_grouped(df: pd.DataFrame) -> AggregateCheckResult:
    """Ensure aggregated groups contain at least one member."""

    values = pd.to_numeric(df["n_grouped"], errors="coerce")
    mask = values.isna() | (values < 1)
    details = df.loc[mask, ["row_index", "cusp_30m_id", "n_grouped", "year", "date"]].copy()
    return AggregateCheckResult(
        mask=mask,
        details=details,
        stats={"n_invalid_n_grouped": int(mask.sum())},
    )


def check_membership_integrity(aggregated: pd.DataFrame, membership: pd.DataFrame) -> AggregateCheckResult:
    """Ensure membership rows reference valid aggregation IDs and are unique."""

    aggregated_ids = set(aggregated["cusp_30m_id"].astype("string"))
    missing_parent = ~membership["cusp_30m_id"].astype("string").isin(aggregated_ids)
    duplicate_pairs = membership.duplicated(subset=["cusp_30m_id", "cusp_obs_id"], keep=False)
    mask = missing_parent | duplicate_pairs
    details = membership.loc[mask, ["cusp_30m_id", "cusp_obs_id"]].copy()
    details["flag_missing_parent"] = missing_parent.loc[details.index]
    details["flag_duplicate_pair"] = duplicate_pairs.loc[details.index]
    return AggregateCheckResult(
        mask=mask,
        details=details,
        stats={
            "n_missing_parent": int(missing_parent.sum()),
            "n_duplicate_pairs": int(duplicate_pairs.sum()),
        },
    )
