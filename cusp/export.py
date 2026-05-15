"""Package flat, versioned CUSP release bundles under exports/."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from cusp.citations import build_bibtex_subset
from cusp.data_utils import _ROOT_DIR


DATA_DIR = _ROOT_DIR / "data"
EXPORTS_DIR = _ROOT_DIR / "exports"
DEFAULT_CANONICAL_INPUT = DATA_DIR / "combined.csv"
DEFAULT_MASTER_BIB_INPUT = DATA_DIR / "cusp_sources.bib"
DEFAULT_CHANGES = "- Initial public CUSP release.\n"
REQUIRED_CANONICAL_COLUMNS = {
    "cusp_obs_id",
    "source",
    "site_id",
    "lat",
    "lon",
    "date",
    "pf_observed",
    "thaw_depth",
    "pf_depth",
    "obs_limit",
    "method",
}


@dataclass(frozen=True)
class ArtifactSummary:
    filename: str
    rows: int | None
    size_bytes: int
    sha256: str
    note: str


def normalize_dataset_version(version: str) -> str:
    """Normalize a dataset version string to `vX.Y` form."""

    raw = version.strip()
    if not raw:
        raise ValueError("Dataset version cannot be empty.")
    if raw.startswith("v"):
        raw = raw[1:]
    parts = raw.split(".")
    if len(parts) != 2 or any(not part.isdigit() for part in parts):
        raise ValueError("Dataset version must look like '1.0' or 'v1.0'.")
    return f"v{int(parts[0])}.{int(parts[1])}"


def load_code_version(pyproject_path: Path = _ROOT_DIR / "pyproject.toml") -> str:
    """Return the current package version from pyproject.toml."""

    with pyproject_path.open("rb") as handle:
        pyproject = tomllib.load(handle)
    return str(pyproject["project"]["version"])


def git_commit() -> str:
    """Return the current git commit if available."""

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_ROOT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"
    return result.stdout.strip()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 checksum of a file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_canonical_table(path: Path) -> pd.DataFrame:
    """Load and validate the canonical observation table."""

    df = pd.read_csv(path, low_memory=False)
    missing = sorted(REQUIRED_CANONICAL_COLUMNS.difference(df.columns))
    if missing:
        raise ValueError(f"Canonical input is missing required columns: {missing}")
    return df


def load_observation_feature_table(path: Path, canonical: pd.DataFrame) -> pd.DataFrame:
    """Load and validate an observation-level feature table keyed to `cusp_obs_id`."""

    features = pd.read_csv(path, low_memory=False)
    if "cusp_obs_id" not in features.columns:
        raise ValueError(
            "Official feature export must be keyed to 'cusp_obs_id'. "
            "Aggregation-keyed feature tables are not valid official release artifacts."
        )
    if features["cusp_obs_id"].isna().any():
        raise ValueError("Feature table contains missing 'cusp_obs_id' values.")
    if features["cusp_obs_id"].duplicated().any():
        raise ValueError("Feature table contains duplicate 'cusp_obs_id' values.")

    canonical_ids = canonical["cusp_obs_id"].astype(str)
    feature_ids = features["cusp_obs_id"].astype(str)
    missing = sorted(set(canonical_ids).difference(feature_ids))
    extra = sorted(set(feature_ids).difference(canonical_ids))
    if missing or extra:
        pieces: list[str] = []
        if missing:
            pieces.append(f"{len(missing)} canonical IDs missing from the feature table")
        if extra:
            pieces.append(f"{len(extra)} feature IDs not present in the canonical table")
        raise ValueError("Feature table does not align to canonical observations: " + "; ".join(pieces))

    ordered = canonical[["cusp_obs_id"]].merge(features, on="cusp_obs_id", how="left", validate="one_to_one")
    return ordered


def build_release_bib(canonical: pd.DataFrame, master_bib_path: Path) -> str:
    """Build the release BibTeX file for the sources present in the canonical table."""

    source_keys = sorted(canonical["source"].dropna().astype(str).unique().tolist())
    bib_text, missing = build_bibtex_subset(source_keys, master_bib_path=master_bib_path)
    if missing:
        raise ValueError(f"Missing BibTeX entries for included release sources: {missing}")
    return bib_text


def copy_text(path: Path, text: str) -> None:
    """Write UTF-8 text to a path, creating parents when needed."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_file(src: Path, dst: Path) -> None:
    """Copy a file, creating parents when needed."""

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def summarize_artifact(path: Path, note: str, rows: int | None = None) -> ArtifactSummary:
    """Build a release summary entry for an exported artifact."""

    return ArtifactSummary(
        filename=path.name,
        rows=rows,
        size_bytes=path.stat().st_size,
        sha256=sha256_file(path),
        note=note,
    )


def artifact_table_markdown(artifacts: list[ArtifactSummary]) -> str:
    """Render the exported artifact summary table."""

    lines = [
        "| File | Rows | Size (bytes) | SHA-256 | Note |",
        "|---|---:|---:|---|---|",
    ]
    for artifact in artifacts:
        row_value = "" if artifact.rows is None else str(artifact.rows)
        lines.append(
            f"| `{artifact.filename}` | {row_value} | {artifact.size_bytes} | "
            f"`{artifact.sha256}` | {artifact.note} |"
        )
    return "\n".join(lines)


def release_info_markdown(
    *,
    dataset_version: str,
    code_version: str,
    commit: str,
    generated_at_utc: str,
    canonical: pd.DataFrame,
    artifacts: list[ArtifactSummary],
    changes_markdown: str,
    features_note: str,
) -> str:
    """Render the human-readable release info file."""

    source_count = canonical["source"].nunique()
    date_min = canonical["date"].min()
    date_max = canonical["date"].max()
    return (
        f"# CUSP Release {dataset_version}\n\n"
        f"## Summary\n\n"
        f"- Dataset version: `{dataset_version}`\n"
        f"- Code version: `{code_version}`\n"
        f"- Git commit: `{commit}`\n"
        f"- Generated at (UTC): `{generated_at_utc}`\n"
        f"- Canonical rows: `{len(canonical)}`\n"
        f"- Included sources: `{source_count}`\n"
        f"- Date range: `{date_min}` to `{date_max}`\n"
        f"- Feature export: {features_note}\n\n"
        f"## Exported Artifacts\n\n"
        f"{artifact_table_markdown(artifacts)}\n\n"
        f"## Changes In This Release\n\n"
        f"{changes_markdown.strip()}\n\n"
        f"## Citation Notes\n\n"
        f"- The canonical dataset file is `cusp_{dataset_version}.csv`.\n"
        f"- The master bibliography file is `cusp_sources_{dataset_version}.bib`.\n"
        f"- To extract only the entries you need from a filtered CUSP table, run:\n\n"
        f"```bash\n"
        f"python -m cusp.citations --input path/to/your_cusp_table.csv --output references.bib\n"
        f"```\n"
    )


def export_release_bundle(
    *,
    dataset_version: str,
    canonical_input: Path = DEFAULT_CANONICAL_INPUT,
    features_input: Path | None = None,
    master_bib_input: Path = DEFAULT_MASTER_BIB_INPUT,
    export_root: Path = EXPORTS_DIR,
    changes_markdown: str = DEFAULT_CHANGES,
) -> tuple[Path, Path]:
    """Export the flat, versioned release bundle to archived and latest directories."""

    version_tag = normalize_dataset_version(dataset_version)
    canonical = load_canonical_table(canonical_input)
    features = None if features_input is None else load_observation_feature_table(features_input, canonical)
    release_bib = build_release_bib(canonical, master_bib_input)

    archived_dir = export_root / "archived" / version_tag
    latest_dir = export_root / "latest"
    if archived_dir.exists():
        shutil.rmtree(archived_dir)
    if latest_dir.exists():
        shutil.rmtree(latest_dir)
    archived_dir.mkdir(parents=True, exist_ok=True)
    latest_dir.mkdir(parents=True, exist_ok=True)

    canonical_name = f"cusp_{version_tag}.csv"
    features_name = f"cusp_features_{version_tag}.csv"
    bib_name = f"cusp_sources_{version_tag}.bib"
    release_info_name = "RELEASE_INFO.md"

    canonical_archived_path = archived_dir / canonical_name
    canonical.to_csv(canonical_archived_path, index=False)
    artifacts: list[ArtifactSummary] = [
        summarize_artifact(canonical_archived_path, "Canonical CUSP dataset.", rows=len(canonical))
    ]

    features_note = "not included"
    if features is not None:
        features_archived_path = archived_dir / features_name
        features.to_csv(features_archived_path, index=False)
        artifacts.append(
            summarize_artifact(
                features_archived_path,
                "Observation-level GEE feature table keyed to cusp_obs_id.",
                rows=len(features),
            )
        )
        features_note = f"included as `{features_name}`"

    bib_archived_path = archived_dir / bib_name
    copy_text(bib_archived_path, release_bib)
    artifacts.append(
        summarize_artifact(
            bib_archived_path,
            "BibTeX entries for all sources present in the canonical release.",
            rows=int(canonical["source"].nunique()),
        )
    )

    generated_at_utc = datetime.now(timezone.utc).isoformat()
    release_info_path = archived_dir / release_info_name
    copy_text(
        release_info_path,
        release_info_markdown(
            dataset_version=version_tag,
            code_version=load_code_version(),
            commit=git_commit(),
            generated_at_utc=generated_at_utc,
            canonical=canonical,
            artifacts=artifacts,
            changes_markdown=changes_markdown,
            features_note=features_note,
        ),
    )
    artifacts.append(summarize_artifact(release_info_path, "Human-readable release metadata.", rows=None))

    copy_file(canonical_archived_path, latest_dir / canonical_name)
    if features is not None:
        copy_file(archived_dir / features_name, latest_dir / features_name)
    copy_file(bib_archived_path, latest_dir / bib_name)
    copy_file(release_info_path, latest_dir / release_info_name)

    return archived_dir, latest_dir


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for release export packaging."""

    parser = argparse.ArgumentParser(
        description="Package flat, versioned CUSP release bundles under exports/."
    )
    parser.add_argument("--version", required=True, help="Dataset version, for example `1.0` or `v1.0`.")
    parser.add_argument("--canonical-input", type=Path, default=DEFAULT_CANONICAL_INPUT)
    parser.add_argument(
        "--features-input",
        type=Path,
        help=(
            "Optional observation-level feature table keyed to cusp_obs_id. "
            "Aggregation-keyed feature tables are not accepted as official release artifacts."
        ),
    )
    parser.add_argument("--master-bib-input", type=Path, default=DEFAULT_MASTER_BIB_INPUT)
    parser.add_argument("--export-root", type=Path, default=EXPORTS_DIR)
    parser.add_argument(
        "--changes-file",
        type=Path,
        help="Optional markdown file containing the 'Changes in this release' section.",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point for release export packaging."""

    args = parse_args()
    changes_markdown = (
        args.changes_file.read_text(encoding="utf-8") if args.changes_file is not None else DEFAULT_CHANGES
    )
    export_release_bundle(
        dataset_version=args.version,
        canonical_input=args.canonical_input,
        features_input=args.features_input,
        master_bib_input=args.master_bib_input,
        export_root=args.export_root,
        changes_markdown=changes_markdown,
    )


if __name__ == "__main__":
    main()
