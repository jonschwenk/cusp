"""Generate the release-data tracker embedded in the repository README."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from cusp.data_utils import _ROOT_DIR


DEFAULT_LATEST_DIR = _ROOT_DIR / "exports" / "latest"
DEFAULT_README_PATH = _ROOT_DIR / "README.md"
TRACKER_START = "<!-- CUSP_DATA_TRACKER:START -->"
TRACKER_END = "<!-- CUSP_DATA_TRACKER:END -->"
RELEASE_FILENAME = re.compile(r"^cusp_(v\d+\.\d+)\.csv$")
RELEASE_URL = "https://github.com/jonschwenk/cusp/releases/tag/{version}"
REQUIRED_COLUMNS = {"source", "pf_observed", "thaw_depth"}


@dataclass(frozen=True)
class ReleaseTracker:
    version: str
    total_observations: int
    presence_observations: int
    absence_observations: int
    alt_observations: int
    source_count: int


def find_latest_release_csv(latest_dir: Path = DEFAULT_LATEST_DIR) -> Path:
    """Find the single versioned observation CSV in ``exports/latest``."""

    candidates = [
        path
        for path in latest_dir.glob("cusp_v*.csv")
        if RELEASE_FILENAME.fullmatch(path.name)
    ]
    if len(candidates) != 1:
        names = ", ".join(sorted(path.name for path in candidates)) or "none"
        raise ValueError(
            f"Expected exactly one versioned CUSP CSV in {latest_dir}; found {len(candidates)} ({names})."
        )
    return candidates[0]


def summarize_release(release_csv: Path) -> ReleaseTracker:
    """Calculate README tracker values directly from a versioned release."""

    match = RELEASE_FILENAME.fullmatch(release_csv.name)
    if match is None:
        raise ValueError(f"Release filename must look like cusp_vX.Y.csv: {release_csv.name}")

    header = pd.read_csv(release_csv, nrows=0)
    missing = sorted(REQUIRED_COLUMNS.difference(header.columns))
    if missing:
        raise ValueError(f"Release CSV is missing tracker columns: {missing}")

    observations = pd.read_csv(release_csv, usecols=sorted(REQUIRED_COLUMNS), low_memory=False)
    state = pd.to_numeric(observations["pf_observed"], errors="coerce")
    invalid_state = state.isna() | ~state.isin([0, 1])
    if invalid_state.any():
        raise ValueError(f"Release CSV has {int(invalid_state.sum())} invalid pf_observed value(s).")

    return ReleaseTracker(
        version=match.group(1),
        total_observations=int(len(observations)),
        presence_observations=int(state.eq(1).sum()),
        absence_observations=int(state.eq(0).sum()),
        alt_observations=int(observations["thaw_depth"].notna().sum()),
        source_count=int(observations["source"].nunique(dropna=True)),
    )


def render_tracker(tracker: ReleaseTracker) -> str:
    """Render the generated Markdown block placed between tracker markers."""

    release_url = RELEASE_URL.format(version=tracker.version)
    return (
        f"{TRACKER_START}\n"
        "<table>\n"
        "  <tr>\n"
        f"    <td align=\"center\" width=\"33%\"><strong><a href=\"{release_url}\">"
        f"{tracker.version}</a></strong><br><sub>Latest release</sub></td>\n"
        f"    <td align=\"center\" width=\"33%\"><strong>{tracker.total_observations:,}"
        "</strong><br><sub>Total observations</sub></td>\n"
        f"    <td align=\"center\" width=\"33%\"><strong>{tracker.source_count:,}"
        "</strong><br><sub>Included sources</sub></td>\n"
        "  </tr>\n"
        "  <tr>\n"
        f"    <td align=\"center\"><strong>{tracker.presence_observations:,}"
        "</strong><br><sub>Permafrost presence</sub></td>\n"
        f"    <td align=\"center\"><strong>{tracker.absence_observations:,}"
        "</strong><br><sub>Permafrost absence</sub></td>\n"
        f"    <td align=\"center\"><strong>{tracker.alt_observations:,}"
        "</strong><br><sub>ALT / thaw-depth measurements</sub></td>\n"
        "  </tr>\n"
        "</table>\n"
        "<p><sub><strong>Note:</strong> ALT / thaw-depth measurements also carry a "
        "permafrost state, so this count overlaps the presence/absence counts."
        "</sub></p>\n"
        f"{TRACKER_END}"
    )


def expected_readme(readme_text: str, tracker: ReleaseTracker) -> str:
    """Replace the generated tracker block while preserving all other text."""

    if readme_text.count(TRACKER_START) != 1 or readme_text.count(TRACKER_END) != 1:
        raise ValueError("README must contain exactly one complete CUSP data tracker block.")

    prefix, remainder = readme_text.split(TRACKER_START, 1)
    _, suffix = remainder.split(TRACKER_END, 1)
    return f"{prefix}{render_tracker(tracker)}{suffix}"


def synchronize_readme(
    *,
    readme_path: Path = DEFAULT_README_PATH,
    release_csv: Path | None = None,
    check: bool = False,
) -> bool:
    """Update the README tracker, or return whether it is current in check mode."""

    release_csv = release_csv or find_latest_release_csv()
    tracker = summarize_release(release_csv)
    current_text = readme_path.read_text(encoding="utf-8")
    updated_text = expected_readme(current_text, tracker)
    is_current = current_text == updated_text

    if check or is_current:
        return is_current

    readme_path.write_text(updated_text, encoding="utf-8")
    return True


def build_parser() -> argparse.ArgumentParser:
    """Build the README tracker command-line parser."""

    parser = argparse.ArgumentParser(description="Refresh the generated data tracker in README.md.")
    parser.add_argument("--readme", type=Path, default=DEFAULT_README_PATH)
    parser.add_argument("--release-csv", type=Path)
    parser.add_argument("--check", action="store_true", help="Fail instead of writing when the tracker is stale.")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Refresh or validate the generated README tracker."""

    args = build_parser().parse_args(argv)
    release_csv = args.release_csv or find_latest_release_csv()
    is_current = synchronize_readme(
        readme_path=args.readme,
        release_csv=release_csv,
        check=args.check,
    )
    if args.check and not is_current:
        print(f"README data tracker is stale for {release_csv.name}.")
        return 1

    action = "already current" if args.check else "synchronized"
    print(f"README data tracker {action} for {release_csv.name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
