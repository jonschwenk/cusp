from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


CORE_ID_COLS = ["row_index", "cusp_obs_id", "source", "method", "site_id", "lat", "lon", "date"]
DEPTH_COLS = ["pf_depth", "thaw_depth", "obs_limit"]


def ensure_out_dir(out_dir: Path) -> None:
    """Create an output directory when an audit needs one."""

    out_dir.mkdir(parents=True, exist_ok=True)


def safe_cols(df: pd.DataFrame, cols: list[str]) -> list[str]:
    """Preserve order while dropping duplicates and missing columns."""

    seen: set[str] = set()
    out: list[str] = []
    for column in cols:
        if column in seen:
            continue
        if column in df.columns:
            out.append(column)
            seen.add(column)
    return out


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Write a CSV, creating parent directories if needed."""

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_json(obj: Any, path: Path) -> None:
    """Write a JSON file, creating parent directories if needed."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")
