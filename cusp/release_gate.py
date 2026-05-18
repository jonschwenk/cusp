"""Run the scripted CUSP release gate.

The gate validates the release workflow without mutating official
versioned release directories. Generated gate artifacts are written under
``runs/release_gate`` by default.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_DIR = REPO_ROOT / "runs" / "release_gate"
DEFAULT_CANONICAL = REPO_ROOT / "data" / "cusp_observations.csv"
DEFAULT_FEATURES = REPO_ROOT / "data" / "cusp_observations_features.csv"
DEFAULT_MASTER_BIB = REPO_ROOT / "data" / "cusp_sources.bib"


class GateFailure(RuntimeError):
    """Raised when one release-gate step fails."""


@dataclass
class StepResult:
    name: str
    status: str
    seconds: float
    command: list[str] | None = None
    returncode: int | None = None
    detail: str | None = None


class GateRunner:
    """Small release-gate runner that records every step."""

    def __init__(self, *, run_dir: Path, keep_going: bool = False) -> None:
        self.run_dir = run_dir
        self.keep_going = keep_going
        self.steps: list[StepResult] = []

    def run_command(self, name: str, command: list[str]) -> None:
        print(f"\n[release-gate] {name}", flush=True)
        print("[release-gate] " + " ".join(command), flush=True)
        started = perf_counter()
        completed = subprocess.run(command, cwd=REPO_ROOT)
        seconds = perf_counter() - started
        status = "passed" if completed.returncode == 0 else "failed"
        self.steps.append(
            StepResult(
                name=name,
                status=status,
                seconds=seconds,
                command=command,
                returncode=completed.returncode,
            )
        )
        if completed.returncode != 0:
            message = f"{name} failed with exit code {completed.returncode}"
            if self.keep_going:
                print(f"[release-gate] {message}", flush=True)
                return
            raise GateFailure(message)

    def run_python(self, name: str, *args: str | Path) -> None:
        command = [sys.executable, *[str(arg) for arg in args]]
        self.run_command(name, command)

    def pass_step(self, name: str, detail: str | None = None, seconds: float = 0.0) -> None:
        print(f"\n[release-gate] {name}", flush=True)
        if detail:
            print(f"[release-gate] {detail}", flush=True)
        self.steps.append(StepResult(name=name, status="passed", seconds=seconds, detail=detail))

    def skip_step(self, name: str, detail: str) -> None:
        print(f"\n[release-gate] {name}", flush=True)
        print(f"[release-gate] SKIPPED: {detail}", flush=True)
        self.steps.append(StepResult(name=name, status="skipped", seconds=0.0, detail=detail))

    def write_summary(self, *, ok: bool) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "ok": ok,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "run_dir": display_path(self.run_dir),
            "steps": [asdict(step) for step in self.steps],
        }
        (self.run_dir / "release_gate_summary.json").write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )


def display_path(path: Path) -> str:
    """Return a repo-relative path when possible."""

    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def normalize_version(version: str) -> str:
    """Normalize a dataset version into the export directory tag."""

    raw = version.strip()
    if raw.startswith("v"):
        raw = raw[1:]
    parts = raw.split(".")
    if len(parts) != 2 or any(not part.isdigit() for part in parts):
        raise ValueError("Dataset version must look like '1.0' or 'v1.0'.")
    return f"v{int(parts[0])}.{int(parts[1])}"


def clean_run_dir(path: Path) -> None:
    """Remove the previous gate run directory after checking its location."""

    resolved = path.resolve()
    runs_root = (REPO_ROOT / "runs").resolve()
    if runs_root != resolved and runs_root not in resolved.parents:
        raise ValueError(f"Refusing to clean a release-gate directory outside {runs_root}: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)


def validate_export_bundle(
    *,
    export_root: Path,
    dataset_version: str,
    canonical_input: Path,
    features_input: Path | None,
    report_path: Path,
) -> dict[str, object]:
    """Validate a freshly generated flat release export bundle."""

    version_tag = normalize_version(dataset_version)
    archived_dir = export_root / "archived" / version_tag
    latest_dir = export_root / "latest"

    canonical_name = f"cusp_{version_tag}.csv"
    features_name = f"cusp_features_{version_tag}.csv"
    bib_name = f"cusp_sources_{version_tag}.bib"
    required = [canonical_name, bib_name, "RELEASE_INFO.md"]
    if features_input is not None:
        required.append(features_name)

    problems: list[str] = []
    for directory in [archived_dir, latest_dir]:
        if not directory.exists():
            problems.append(f"Missing export directory: {display_path(directory)}")
            continue
        for filename in required:
            if not (directory / filename).exists():
                problems.append(f"Missing {filename} in {display_path(directory)}")
        aggregated_files = [path.name for path in directory.iterdir() if "aggregated" in path.name.lower()]
        if aggregated_files:
            problems.append(
                f"Aggregation artifacts are not official release files but were found in "
                f"{display_path(directory)}: {aggregated_files}"
            )

    canonical = pd.read_csv(canonical_input, low_memory=False)
    exported = pd.read_csv(archived_dir / canonical_name, low_memory=False)
    if canonical.columns.tolist() != exported.columns.tolist():
        problems.append("Exported canonical table columns do not match the canonical input.")
    if len(canonical) != len(exported):
        problems.append(f"Exported canonical row count {len(exported)} does not match {len(canonical)}.")
    if "cusp_obs_id" in canonical.columns and "cusp_obs_id" in exported.columns:
        canonical_ids = canonical["cusp_obs_id"].astype("string").reset_index(drop=True)
        exported_ids = exported["cusp_obs_id"].astype("string").reset_index(drop=True)
        if not canonical_ids.equals(exported_ids):
            problems.append("Exported canonical cusp_obs_id order does not match the canonical input.")

    feature_rows: int | None = None
    if features_input is not None:
        exported_features = pd.read_csv(archived_dir / features_name, low_memory=False)
        feature_rows = int(len(exported_features))
        if "cusp_obs_id" not in exported_features.columns:
            problems.append("Exported feature table is missing cusp_obs_id.")
        else:
            feature_ids = exported_features["cusp_obs_id"].astype("string").reset_index(drop=True)
            canonical_ids = canonical["cusp_obs_id"].astype("string").reset_index(drop=True)
            if not feature_ids.equals(canonical_ids):
                problems.append("Exported feature table is not aligned to canonical cusp_obs_id order.")
            if exported_features["cusp_obs_id"].duplicated().any():
                problems.append("Exported feature table contains duplicate cusp_obs_id values.")

    report = {
        "ok": not problems,
        "export_root": display_path(export_root),
        "dataset_version": version_tag,
        "canonical_rows": int(len(canonical)),
        "feature_rows": feature_rows,
        "required_files": required,
        "problems": problems,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if problems:
        raise GateFailure("Export bundle validation failed: " + "; ".join(problems))
    return report


def write_feature_smoke_input(source_path: Path, smoke_input_path: Path, rows: int) -> None:
    """Write a small deterministic feature-sampling input from an aggregated table."""

    source = pd.read_csv(source_path, low_memory=False)
    if len(source) < rows:
        raise GateFailure(f"Feature smoke input requested {rows} rows, but only {len(source)} are available.")
    smoke = source.head(rows).copy()
    smoke_input_path.parent.mkdir(parents=True, exist_ok=True)
    smoke.to_csv(smoke_input_path, index=False)


def validate_feature_smoke_output(
    *,
    input_path: Path,
    output_path: Path,
    manifest_path: Path,
    report_path: Path,
) -> dict[str, object]:
    """Validate that the GEE feature smoke test produced aligned output."""

    source = pd.read_csv(input_path, low_memory=False)
    features = pd.read_csv(output_path, low_memory=False)
    id_column = "cusp_30m_id" if "cusp_30m_id" in source.columns else "cusp_obs_id"

    problems: list[str] = []
    if id_column not in features.columns:
        problems.append(f"Feature smoke output is missing {id_column}.")
    if len(source) != len(features):
        problems.append(f"Feature smoke row count {len(features)} does not match input row count {len(source)}.")
    if id_column in features.columns:
        source_ids = source[id_column].astype("string").reset_index(drop=True)
        feature_ids = features[id_column].astype("string").reset_index(drop=True)
        if not source_ids.equals(feature_ids):
            problems.append(f"Feature smoke {id_column} order does not match input order.")
        if features[id_column].duplicated().any():
            problems.append(f"Feature smoke output contains duplicate {id_column} values.")
    if not manifest_path.exists():
        problems.append("Feature smoke manifest was not written.")
        declared_feature_columns: list[str] = []
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        declared_feature_columns = []
        for metadata in manifest.get("features", {}).values():
            declared_feature_columns.extend(metadata.get("output_columns", []))

    identity_columns = {id_column, "date", "year", "lat", "lon"}
    sampled_feature_columns = [column for column in features.columns if column not in identity_columns]
    if declared_feature_columns:
        missing_declared = [column for column in declared_feature_columns if column not in features.columns]
        if missing_declared:
            problems.append(f"Feature smoke output is missing declared feature columns: {missing_declared}.")
    elif not sampled_feature_columns:
        problems.append("Feature smoke output did not contain sampled feature columns.")

    report = {
        "ok": not problems,
        "input_path": display_path(input_path),
        "output_path": display_path(output_path),
        "manifest_path": display_path(manifest_path),
        "rows": int(len(features)),
        "columns": features.columns.tolist(),
        "sampled_feature_columns": sampled_feature_columns,
        "declared_feature_columns": declared_feature_columns,
        "problems": problems,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if problems:
        raise GateFailure("Feature smoke validation failed: " + "; ".join(problems))
    return report


def build_parser() -> argparse.ArgumentParser:
    """Build the release-gate CLI parser."""

    parser = argparse.ArgumentParser(description="Run the CUSP v1 release gate.")
    parser.add_argument("--version", default="1.0", help="Dataset version to validate, for example 1.0 or v1.0.")
    parser.add_argument("--canonical-input", type=Path, default=DEFAULT_CANONICAL)
    parser.add_argument("--features-input", type=Path, default=DEFAULT_FEATURES)
    parser.add_argument("--master-bib-input", type=Path, default=DEFAULT_MASTER_BIB)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--no-clean", action="store_true", help="Do not clear the previous run directory first.")
    parser.add_argument("--keep-going", action="store_true", help="Continue after command failures where possible.")
    parser.add_argument("--skip-tests", action="store_true", help="Skip Python unit tests.")
    parser.add_argument("--skip-docs", action="store_true", help="Skip the strict MkDocs documentation build.")
    parser.add_argument("--skip-feature-export", action="store_true", help="Do not include features in export validation.")
    parser.add_argument("--skip-gee-smoke", action="store_true", help="Skip the live GEE feature-sampling smoke test.")
    parser.add_argument("--gee-project", help="Earth Engine project for the live feature smoke test.")
    parser.add_argument("--feature-smoke-rows", type=int, default=5, help="Rows sampled in the GEE smoke test.")
    parser.add_argument(
        "--feature-smoke-features",
        help=(
            "Comma-separated feature families for the smoke test. "
            "Defaults to the full base_v1 feature set on a small input."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the release gate."""

    args = build_parser().parse_args(argv)
    run_dir = args.run_dir if args.run_dir.is_absolute() else REPO_ROOT / args.run_dir
    if args.no_clean:
        run_dir.mkdir(parents=True, exist_ok=True)
    else:
        clean_run_dir(run_dir)

    runner = GateRunner(run_dir=run_dir, keep_going=args.keep_going)
    ok = False
    try:
        if args.skip_tests:
            runner.skip_step("Unit tests", "--skip-tests was supplied.")
        else:
            runner.run_python("Unit tests", "-m", "unittest", "discover", "-s", "tests")

        if args.skip_docs:
            runner.skip_step("Strict documentation build", "--skip-docs was supplied.")
        else:
            runner.run_python("Strict documentation build", "-m", "mkdocs", "build", "--strict")

        observations_qc_dir = run_dir / "qc_observations"
        runner.run_python(
            "Full observation-level QA/QC",
            "-m",
            "cusp.qc",
            "validate-observations",
            "--input",
            args.canonical_input,
            "--out",
            observations_qc_dir,
        )

        export_root = run_dir / "exports"
        export_command = [
            "-m",
            "cusp.export",
            "--version",
            args.version,
            "--canonical-input",
            args.canonical_input,
            "--master-bib-input",
            args.master_bib_input,
            "--export-root",
            export_root,
        ]
        features_input = None
        if not args.skip_feature_export:
            if not args.features_input.exists():
                raise GateFailure(
                    f"Feature export validation requested, but {display_path(args.features_input)} does not exist. "
                    "Pass --skip-feature-export to validate a release without the optional feature artifact."
                )
            features_input = args.features_input
            export_command.extend(["--features-input", features_input])
        runner.run_python("Export bundle generation", *export_command)
        started = perf_counter()
        report = validate_export_bundle(
            export_root=export_root,
            dataset_version=args.version,
            canonical_input=args.canonical_input,
            features_input=features_input,
            report_path=run_dir / "export_validation.json",
        )
        runner.pass_step(
            "Export bundle validation",
            detail=f"Validated {report['required_files']} under {display_path(export_root)}",
            seconds=perf_counter() - started,
        )

        aggregation_dir = run_dir / "aggregation"
        aggregated_csv = aggregation_dir / "aggregated_30m.csv"
        membership_csv = aggregation_dir / "aggregated_30m_membership.csv"
        flags_csv = aggregation_dir / "aggregated_30m_qc_flags.csv"
        excluded_csv = aggregation_dir / "aggregated_30m_excluded_rows.csv"
        gpkg_path = aggregation_dir / "aggregated_30m.gpkg"
        manifest_path = aggregation_dir / "aggregated_30m_manifest.json"
        runner.run_python(
            "Supported aggregation workflow rebuild",
            "-m",
            "cusp.aggregate",
            "--input",
            args.canonical_input,
            "--output",
            aggregated_csv,
            "--membership-output",
            membership_csv,
            "--flags-output",
            flags_csv,
            "--excluded-output",
            excluded_csv,
            "--gpkg-output",
            gpkg_path,
            "--manifest-output",
            manifest_path,
        )
        runner.run_python(
            "Supported aggregation workflow validation",
            "-m",
            "cusp.qc",
            "validate-aggregated",
            "--input",
            aggregated_csv,
            "--membership",
            membership_csv,
            "--out",
            run_dir / "qc_aggregated",
        )

        if args.skip_gee_smoke:
            runner.skip_step("Limited GEE feature-sampling smoke test", "--skip-gee-smoke was supplied.")
        elif not args.gee_project:
            raise GateFailure("The GEE feature smoke test requires --gee-project or explicit --skip-gee-smoke.")
        else:
            feature_dir = run_dir / "feature_smoke"
            smoke_input = feature_dir / "aggregated_30m_smoke_input.csv"
            smoke_output = feature_dir / "aggregated_30m_smoke_features.csv"
            smoke_manifest = feature_dir / "aggregated_30m_smoke_features_manifest.json"
            write_feature_smoke_input(aggregated_csv, smoke_input, rows=args.feature_smoke_rows)

            feature_command = [
                "-m",
                "cusp.features",
                "--input",
                smoke_input,
                "--output",
                smoke_output,
                "--manifest",
                smoke_manifest,
                "--gee-project",
                args.gee_project,
                "--chunk-size",
                str(args.feature_smoke_rows),
                "--resume",
            ]
            if args.feature_smoke_features:
                feature_command.extend(["--feature-set", "none", "--features", args.feature_smoke_features])
            runner.run_python("Limited GEE feature-sampling smoke test", *feature_command)
            started = perf_counter()
            smoke_report = validate_feature_smoke_output(
                input_path=smoke_input,
                output_path=smoke_output,
                manifest_path=smoke_manifest,
                report_path=feature_dir / "feature_smoke_validation.json",
            )
            runner.pass_step(
                "Feature smoke output validation",
                detail=f"Validated {smoke_report['rows']} feature smoke rows.",
                seconds=perf_counter() - started,
            )

        ok = all(step.status in {"passed", "skipped"} for step in runner.steps)
        if ok:
            print(f"\n[release-gate] PASS. Summary: {display_path(run_dir / 'release_gate_summary.json')}")
        return 0 if ok else 1
    except GateFailure as exc:
        print(f"\n[release-gate] FAIL: {exc}", file=sys.stderr, flush=True)
        return 1
    finally:
        runner.write_summary(ok=ok)


if __name__ == "__main__":
    raise SystemExit(main())
