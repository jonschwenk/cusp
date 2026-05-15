"""
Utilities for structured, parseable metadata stored in source-processing script
module docstrings.
"""

from __future__ import annotations

import ast
import csv
import re
import tomllib
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
DEFAULT_OUTPUT = REPO_ROOT / "PROCESS_SCRIPT_METADATA.csv"

SCHEMA_VERSION = 1
SCRIPT_PREFIXES = ("process_",)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

ALLOWED_RELEASE_CLEARANCE = {
    "approved",
    "needs_review",
    "deferred",
    "do_not_release",
}

ALLOWED_PERMISSION_BASIS = {
    "self_generated",
    "published_literature",
    "public_repository_terms",
    "emailed_approval",
    "verbal_approval",
    "institutional_approval",
    "other",
    "needs_review",
}

REQUIRED_STRING_FIELDS = (
    "source_key",
    "release_clearance",
    "permission_basis",
    "last_substantive_update",
    "source_dataset",
)

OPTIONAL_STRING_FIELDS = (
    "original_author",
    "notes",
)

REQUIRED_LIST_FIELDS = (
    "processing_assumptions",
    "manual_steps",
    "known_limitations",
    "external_dependencies",
)

OPTIONAL_LIST_FIELDS = (
    "temporal_handling",
    "spatial_handling",
)

CSV_COLUMNS = (
    "source_directory",
    "processing_script",
    "processed_output",
    "metadata_status",
    "structured_metadata_present",
    "validation_error_count",
    "validation_errors",
    "source_key",
    "release_clearance",
    "permission_basis",
    "original_author",
    "last_substantive_update",
    "manual_steps_required",
    "external_dependencies_required",
    "source_dataset",
    "processing_assumptions",
    "temporal_handling",
    "spatial_handling",
    "manual_steps",
    "known_limitations",
    "external_dependencies",
    "notes",
)


def is_process_script(path: Path) -> bool:
    return path.suffix == ".py" and path.name.startswith(SCRIPT_PREFIXES)


def discover_process_scripts(repo_root: Path | None = None) -> list[Path]:
    root = repo_root or REPO_ROOT
    data_dir = root / "data"
    scripts = []
    for source_dir in sorted(p for p in data_dir.iterdir() if p.is_dir()):
        scripts.extend(sorted(p for p in source_dir.iterdir() if is_process_script(p)))
    return scripts


def read_script_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("utf-8", b"", 0, 1, f"Could not decode {path}")


def extract_module_docstring(path: Path) -> tuple[str | None, str | None]:
    try:
        text = read_script_text(path)
        module = ast.parse(text)
    except SyntaxError as exc:
        return None, f"syntax_error: {exc.msg} (line {exc.lineno})"
    except UnicodeDecodeError as exc:
        return None, f"decode_error: {exc}"
    return ast.get_docstring(module, clean=False), None


def parse_structured_metadata(docstring: str | None, script_path: Path) -> tuple[str, dict[str, object], list[str]]:
    if docstring is None:
        return "missing_docstring", {}, []

    parse_errors: list[str] = []
    try:
        data = tomllib.loads(docstring)
    except tomllib.TOMLDecodeError as exc:
        if "metadata_schema_version" in docstring:
            parse_errors.append(f"TOML parse error: {exc}")
            return "parse_error", {}, parse_errors
        return "legacy_unstructured", {}, []

    if "metadata_schema_version" not in data:
        return "legacy_unstructured", {}, []

    errors = validate_metadata_dict(data, script_path)
    return "structured_toml", data, errors


def validate_metadata_dict(metadata: dict[str, object], script_path: Path) -> list[str]:
    errors: list[str] = []
    source_dir = script_path.parent.name

    if metadata.get("metadata_schema_version") != SCHEMA_VERSION:
        errors.append(
            f"metadata_schema_version must be {SCHEMA_VERSION}, got {metadata.get('metadata_schema_version')!r}"
        )

    for field in REQUIRED_STRING_FIELDS:
        value = metadata.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} must be a non-empty string")

    for field in OPTIONAL_STRING_FIELDS:
        value = metadata.get(field, "")
        if value != "" and not isinstance(value, str):
            errors.append(f"{field} must be a string when provided")

    for field in REQUIRED_LIST_FIELDS + OPTIONAL_LIST_FIELDS:
        value = metadata.get(field, [] if field in OPTIONAL_LIST_FIELDS else None)
        if field in REQUIRED_LIST_FIELDS and value is None:
            errors.append(f"{field} must be a list of strings")
            continue
        if value is None:
            continue
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            errors.append(f"{field} must be a list of strings")

    if isinstance(metadata.get("source_key"), str) and metadata["source_key"] != source_dir:
        errors.append(
            f"source_key {metadata['source_key']!r} does not match source directory {source_dir!r}"
        )

    release_clearance = metadata.get("release_clearance")
    if release_clearance not in ALLOWED_RELEASE_CLEARANCE:
        errors.append(
            f"release_clearance must be one of {sorted(ALLOWED_RELEASE_CLEARANCE)}, got {release_clearance!r}"
        )

    permission_basis = metadata.get("permission_basis")
    if permission_basis not in ALLOWED_PERMISSION_BASIS:
        errors.append(
            f"permission_basis must be one of {sorted(ALLOWED_PERMISSION_BASIS)}, got {permission_basis!r}"
        )

    for field in ("last_substantive_update",):
        value = metadata.get(field, "")
        if value and (not isinstance(value, str) or DATE_RE.match(value) is None):
            errors.append(f"{field} must use YYYY-MM-DD when provided")

    return errors


def find_processed_output(source_dir: Path) -> str:
    exact = source_dir / f"processed_{source_dir.name.lower()}.csv"
    if exact.exists():
        return path_display(exact)

    matches = sorted(source_dir.glob("processed_*.csv"))
    if len(matches) == 1:
        return path_display(matches[0])
    if len(matches) > 1:
        return " || ".join(path_display(match) for match in matches)
    return ""


def join_items(value: object) -> str:
    if not value:
        return ""
    if isinstance(value, list):
        return " || ".join(str(item) for item in value)
    return str(value)


def blank_metadata_values() -> dict[str, str]:
    keys = (
        "source_key",
        "release_clearance",
        "permission_basis",
        "original_author",
        "last_substantive_update",
        "source_dataset",
        "processing_assumptions",
        "temporal_handling",
        "spatial_handling",
        "manual_steps",
        "known_limitations",
        "external_dependencies",
        "notes",
    )
    return {key: "" for key in keys}


def path_display(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def build_metadata_record(script_path: Path, strict: bool = False) -> dict[str, str]:
    docstring, extraction_error = extract_module_docstring(script_path)
    source_dir = script_path.parent
    record = {
        "source_directory": source_dir.name,
        "processing_script": path_display(script_path),
        "processed_output": find_processed_output(source_dir),
        "metadata_status": "",
        "structured_metadata_present": "no",
        "validation_error_count": "0",
        "validation_errors": "",
        "manual_steps_required": "",
        "external_dependencies_required": "",
    }
    record.update(blank_metadata_values())

    if extraction_error:
        errors = [extraction_error]
        status = "parse_error"
        metadata: dict[str, object] = {}
    else:
        status, metadata, errors = parse_structured_metadata(docstring, script_path)

    if strict and status != "structured_toml":
        errors.append("Structured metadata is required in strict mode")

    if status == "structured_toml":
        record["structured_metadata_present"] = "yes"
        for field in REQUIRED_STRING_FIELDS + OPTIONAL_STRING_FIELDS:
            value = metadata.get(field, "")
            record[field] = value if isinstance(value, str) else ""
        for field in REQUIRED_LIST_FIELDS + OPTIONAL_LIST_FIELDS:
            record[field] = join_items(metadata.get(field, []))
        record["manual_steps_required"] = "yes" if metadata.get("manual_steps") else "no"
        record["external_dependencies_required"] = "yes" if metadata.get("external_dependencies") else "no"

    record["metadata_status"] = status
    record["validation_error_count"] = str(len(errors))
    record["validation_errors"] = " || ".join(errors)
    return record


def build_metadata_records(script_paths: list[Path], strict: bool = False) -> list[dict[str, str]]:
    return [build_metadata_record(path, strict=strict) for path in sorted(script_paths)]


def write_metadata_csv(records: list[dict[str, str]], output_path: Path) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(records)


def summarize_records(records: list[dict[str, str]]) -> str:
    counter = Counter(record["metadata_status"] for record in records)
    parts = [f"{status}={count}" for status, count in sorted(counter.items())]
    total_errors = sum(int(record["validation_error_count"]) for record in records)
    parts.append(f"validation_errors={total_errors}")
    return ", ".join(parts)
