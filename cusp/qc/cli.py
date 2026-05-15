"""Supported CLI entry points for CUSP QA validation and auditing."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from cusp.aggregate import AGGREGATED_COLUMNS
from cusp.build import CANONICAL_COLUMNS

from .aggregate import (
    check_cusp_30m_id,
    check_membership_integrity,
    check_n_grouped,
    check_pf_observed_fraction,
    load_aggregated_csv,
)
from .checks import (
    DEFAULT_FUTURE_YEAR_BUFFER,
    DEFAULT_TOO_OLD_YEAR,
    check_coordinates,
    check_cusp_obs_id,
    check_dates,
    check_negative_depths,
    check_pf_observed_values,
    check_suspect_swapped_latlon,
    check_thaw_depth_gt_pf_depth,
    check_zero_obs_limit,
)
from .io import load_combined_csv
from .reporting import ensure_out_dir, write_csv, write_json


EXPECTED_COMBINED_COLUMNS = ["row_index"] + CANONICAL_COLUMNS
EXPECTED_AGGREGATED_COLUMNS = ["row_index"] + AGGREGATED_COLUMNS


@dataclass(frozen=True)
class ValidationRunResult:
    ok: bool
    summary: dict[str, Any]


@dataclass
class AuditSummary:
    input_path: str
    n_rows: int
    n_cols: int
    cutoff_future_year: int
    n_missing_cusp_obs_id: int
    n_duplicate_cusp_obs_id: int
    n_date_unparseable: int
    n_date_future: int
    n_date_too_old: int
    n_missing_xy: int
    n_invalid_xy_range: int
    n_negative_pf_depth: int
    n_negative_thaw_depth: int
    n_negative_obs_limit: int
    n_zero_obs_limit: int
    n_invalid_pf_observed: int
    n_thaw_gt_pf_diagnostic: int
    n_suspect_swapped_latlon: int
    pf_observed_counts: dict[str, int]


def _schema_details(expected: list[str], actual: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "expected_columns": json.dumps(expected),
                "actual_columns": json.dumps(actual),
            }
        ]
    )


def _write_if_nonempty(df_out: pd.DataFrame, path: Path) -> None:
    if df_out is None or df_out.empty:
        return
    write_csv(df_out, path)


def run_combined_validation(
    input_path: str | Path,
    *,
    out_dir: str | Path | None = None,
    too_old_year: int = DEFAULT_TOO_OLD_YEAR,
    future_year_buffer: int = DEFAULT_FUTURE_YEAR_BUFFER,
) -> ValidationRunResult:
    """Run the supported hard-gate validation on combined.csv."""

    input_path = Path(input_path)
    df = load_combined_csv(input_path)

    counts: dict[str, int] = {}
    outputs: list[tuple[str, pd.DataFrame]] = []

    schema_ok = df.columns.tolist() == EXPECTED_COMBINED_COLUMNS
    counts["schema_mismatch"] = 0 if schema_ok else 1
    if not schema_ok:
        outputs.append(("schema_mismatch.csv", _schema_details(EXPECTED_COMBINED_COLUMNS, df.columns.tolist())))

    id_res = check_cusp_obs_id(df)
    counts["invalid_cusp_obs_id"] = id_res.count()
    outputs.append(("invalid_cusp_obs_id.csv", id_res.details))

    pf_res = check_pf_observed_values(df)
    counts["invalid_pf_observed"] = pf_res.count()
    outputs.append(("invalid_pf_observed.csv", pf_res.details))

    coord_res = check_coordinates(df)
    counts["invalid_coordinates"] = coord_res.count()
    outputs.append(("invalid_coordinates.csv", coord_res.details))

    date_res = check_dates(df, too_old_year=too_old_year, future_year_buffer=future_year_buffer)
    counts["bad_dates"] = date_res.count()
    outputs.append(("bad_dates.csv", date_res.details))

    depth_res = check_negative_depths(df)
    counts["bad_depths"] = depth_res.count()
    outputs.append(("bad_depths.csv", depth_res.details))

    zero_res = check_zero_obs_limit(df)
    counts["zero_obs_limit"] = zero_res.count()
    outputs.append(("zero_obs_limit.csv", zero_res.details))

    ok = all(value == 0 for value in counts.values())
    summary = {
        "validation_scope": "combined",
        "input_path": str(input_path),
        "ok": ok,
        "counts": counts,
        "n_rows": int(len(df)),
        "n_cols": int(len(df.columns)),
    }

    if out_dir is not None:
        out_dir = Path(out_dir)
        ensure_out_dir(out_dir)
        for filename, details in outputs:
            _write_if_nonempty(details, out_dir / filename)
        write_json(summary, out_dir / "validation_summary.json")

    return ValidationRunResult(ok=ok, summary=summary)


def run_aggregated_validation(
    aggregated_path: str | Path,
    *,
    membership_path: str | Path,
    out_dir: str | Path | None = None,
) -> ValidationRunResult:
    """Run the supported hard-gate validation on aggregated_30m outputs."""

    aggregated_path = Path(aggregated_path)
    membership_path = Path(membership_path)
    aggregated = load_aggregated_csv(str(aggregated_path))
    membership = pd.read_csv(membership_path, low_memory=False)

    counts: dict[str, int] = {}
    outputs: list[tuple[str, pd.DataFrame]] = []

    schema_ok = aggregated.columns.tolist() == EXPECTED_AGGREGATED_COLUMNS
    counts["schema_mismatch"] = 0 if schema_ok else 1
    if not schema_ok:
        outputs.append(("schema_mismatch.csv", _schema_details(EXPECTED_AGGREGATED_COLUMNS, aggregated.columns.tolist())))

    id_res = check_cusp_30m_id(aggregated)
    counts["invalid_cusp_30m_id"] = id_res.count()
    outputs.append(("invalid_cusp_30m_id.csv", id_res.details))

    pf_res = check_pf_observed_fraction(aggregated)
    counts["invalid_pf_observed_fraction"] = pf_res.count()
    outputs.append(("invalid_pf_observed_fraction.csv", pf_res.details))

    grouped_res = check_n_grouped(aggregated)
    counts["invalid_n_grouped"] = grouped_res.count()
    outputs.append(("invalid_n_grouped.csv", grouped_res.details))

    membership_res = check_membership_integrity(aggregated, membership)
    counts["invalid_membership"] = membership_res.count()
    outputs.append(("invalid_membership.csv", membership_res.details))

    ok = all(value == 0 for value in counts.values())
    summary = {
        "validation_scope": "aggregated_30m",
        "input_path": str(aggregated_path),
        "membership_path": str(membership_path),
        "ok": ok,
        "counts": counts,
        "n_rows": int(len(aggregated)),
        "n_cols": int(len(aggregated.columns)),
    }

    if out_dir is not None:
        out_dir = Path(out_dir)
        ensure_out_dir(out_dir)
        for filename, details in outputs:
            _write_if_nonempty(details, out_dir / filename)
        write_json(summary, out_dir / "validation_summary.json")

    return ValidationRunResult(ok=ok, summary=summary)


def run_combined_audit(
    input_path: str | Path,
    *,
    out_dir: str | Path,
    too_old_year: int = DEFAULT_TOO_OLD_YEAR,
    clean: bool = True,
) -> dict[str, Any]:
    """Run the diagnostic combined.csv audit and write outputs."""

    input_path = Path(input_path)
    out_dir = Path(out_dir)
    if out_dir.exists() and clean:
        shutil.rmtree(out_dir)
    ensure_out_dir(out_dir)

    df = load_combined_csv(input_path)

    id_res = check_cusp_obs_id(df)
    _write_if_nonempty(id_res.details, out_dir / "invalid_cusp_obs_id.csv")

    dates_res = check_dates(df, too_old_year=too_old_year)
    _write_if_nonempty(dates_res.details, out_dir / "bad_dates.csv")

    coords_res = check_coordinates(df)
    _write_if_nonempty(coords_res.details, out_dir / "invalid_coordinates.csv")

    depths_res = check_negative_depths(df)
    _write_if_nonempty(depths_res.details, out_dir / "bad_depths.csv")

    zero_obs_limit_res = check_zero_obs_limit(df)
    _write_if_nonempty(zero_obs_limit_res.details, out_dir / "zero_obs_limit.csv")

    pf_obs_res = check_pf_observed_values(df)
    _write_if_nonempty(pf_obs_res.details, out_dir / "invalid_pf_observed.csv")

    thaw_pf_res = check_thaw_depth_gt_pf_depth(df)
    _write_if_nonempty(thaw_pf_res.details, out_dir / "thaw_depth_gt_pf_depth.csv")

    swapped_res = check_suspect_swapped_latlon(df)
    _write_if_nonempty(swapped_res.details, out_dir / "suspect_swapped_latlon.csv")

    if {"source", "method"}.issubset(df.columns):
        counts = (
            df.groupby(["source", "method"], dropna=False)
            .size()
            .reset_index(name="n")
            .sort_values("n", ascending=False)
        )
        write_csv(counts, out_dir / "counts_by_method_source.csv")

    if "source" in df.columns:
        by_source = (
            df.groupby("source", dropna=False)
            .size()
            .reset_index(name="n")
            .sort_values("n", ascending=False)
        )
        write_csv(by_source, out_dir / "counts_by_source.csv")

    if {"source", "method"}.issubset(df.columns):
        grouped = df.groupby(["source", "method"], dropna=False)
        stats = []
        for (source, method), dfg in grouped:
            record: dict[str, Any] = {"source": source, "method": method, "n": int(len(dfg))}
            for column in ["pf_depth", "thaw_depth", "obs_limit"]:
                if column not in dfg.columns:
                    continue
                series = pd.to_numeric(dfg[column], errors="coerce")
                record[f"{column}_nonnull"] = int(series.notna().sum())
                if series.notna().any():
                    record[f"{column}_p50"] = float(series.quantile(0.50))
                    record[f"{column}_p90"] = float(series.quantile(0.90))
                    record[f"{column}_p99"] = float(series.quantile(0.99))
                    record[f"{column}_max"] = float(series.max())
            stats.append(record)
        write_csv(pd.DataFrame.from_records(stats), out_dir / "depth_stats_by_source_method.csv")

    pf_counts: dict[str, int] = {}
    if "pf_observed" in df.columns:
        values = pd.to_numeric(df["pf_observed"], errors="coerce")
        for key, value in values.value_counts(dropna=False).items():
            pf_counts[str(key)] = int(value)

    cutoff_future_year = int((dates_res.stats or {}).get("cutoff_future_year", 0))
    summary = AuditSummary(
        input_path=str(input_path),
        n_rows=int(len(df)),
        n_cols=int(len(df.columns)),
        cutoff_future_year=cutoff_future_year,
        n_missing_cusp_obs_id=int((id_res.stats or {}).get("n_missing_cusp_obs_id", 0)),
        n_duplicate_cusp_obs_id=int((id_res.stats or {}).get("n_duplicate_cusp_obs_id", 0)),
        n_date_unparseable=int((dates_res.stats or {}).get("n_date_unparseable", 0)),
        n_date_future=int((dates_res.stats or {}).get("n_date_future", 0)),
        n_date_too_old=int((dates_res.stats or {}).get("n_date_too_old", 0)),
        n_missing_xy=int((coords_res.stats or {}).get("n_missing_xy", 0)),
        n_invalid_xy_range=int((coords_res.stats or {}).get("n_invalid_xy_range", 0)),
        n_negative_pf_depth=int((depths_res.stats or {}).get("n_negative_pf_depth", 0)),
        n_negative_thaw_depth=int((depths_res.stats or {}).get("n_negative_thaw_depth", 0)),
        n_negative_obs_limit=int((depths_res.stats or {}).get("n_negative_obs_limit", 0)),
        n_zero_obs_limit=int((zero_obs_limit_res.stats or {}).get("n_zero_obs_limit", 0)),
        n_invalid_pf_observed=int((pf_obs_res.stats or {}).get("n_invalid_pf_observed", 0)),
        n_thaw_gt_pf_diagnostic=int((thaw_pf_res.stats or {}).get("n_thaw_gt_pf", 0)),
        n_suspect_swapped_latlon=int((swapped_res.stats or {}).get("n_suspect_swapped_latlon", 0)),
        pf_observed_counts=pf_counts,
    )

    payload = asdict(summary)
    write_json(payload, out_dir / "qc_summary.json")
    return payload


def build_parser() -> argparse.ArgumentParser:
    """Build the supported CUSP QC CLI parser."""

    parser = argparse.ArgumentParser(description="Validate or audit release-facing CUSP artifacts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    combined = subparsers.add_parser("validate-combined", help="Run hard-gate validation on combined.csv.")
    combined.add_argument("--input", type=Path, default=Path("data/combined.csv"))
    combined.add_argument("--out", type=Path, help="Optional output directory for failure reports.")
    combined.add_argument("--too-old-year", type=int, default=DEFAULT_TOO_OLD_YEAR)
    combined.add_argument("--future-year-buffer", type=int, default=DEFAULT_FUTURE_YEAR_BUFFER)

    aggregated = subparsers.add_parser("validate-aggregated", help="Run hard-gate validation on aggregated_30m artifacts.")
    aggregated.add_argument("--input", type=Path, default=Path("data/aggregated_30m.csv"))
    aggregated.add_argument("--membership", type=Path, default=Path("data/aggregated_30m_membership.csv"))
    aggregated.add_argument("--out", type=Path, help="Optional output directory for failure reports.")

    audit = subparsers.add_parser("audit-combined", help="Run the diagnostic combined.csv audit.")
    audit.add_argument("--input", type=Path, default=Path("data/combined.csv"))
    audit.add_argument("--out", type=Path, default=Path("outputs/qc_audit"))
    audit.add_argument("--too-old-year", type=int, default=DEFAULT_TOO_OLD_YEAR)
    audit.add_argument("--no-clean", action="store_true", help="Do not clear the output directory before writing.")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the supported CUSP QC CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate-combined":
        result = run_combined_validation(
            args.input,
            out_dir=args.out,
            too_old_year=args.too_old_year,
            future_year_buffer=args.future_year_buffer,
        )
        print(json.dumps(result.summary, indent=2))
        return 0 if result.ok else 1

    if args.command == "validate-aggregated":
        result = run_aggregated_validation(
            args.input,
            membership_path=args.membership,
            out_dir=args.out,
        )
        print(json.dumps(result.summary, indent=2))
        return 0 if result.ok else 1

    if args.command == "audit-combined":
        payload = run_combined_audit(
            args.input,
            out_dir=args.out,
            too_old_year=args.too_old_year,
            clean=not args.no_clean,
        )
        print(f"Wrote QC audit outputs to: {args.out}")
        print(json.dumps(payload, indent=2))
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2
