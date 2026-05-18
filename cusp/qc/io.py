from __future__ import annotations

from pathlib import Path

import pandas as pd

from .reporting import DEPTH_COLS


def load_observations_csv(path: Path) -> pd.DataFrame:
    """Load the canonical observation bundle in a QA-friendly form."""

    df = pd.read_csv(path, low_memory=False)
    df = df.copy()

    if "row_index" in df.columns:
        df = df.rename(columns={"row_index": "row_index_input"})

    df.insert(0, "row_index", df.index)

    for column in ["lat", "lon", "pf_observed"] + DEPTH_COLS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    return df


def load_combined_csv(path: Path) -> pd.DataFrame:
    """Compatibility alias for the old observation artifact name."""

    return load_observations_csv(path)
