"""Load and enforce the frozen canonical CUSP observation contract."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_CONTRACT_PATH = Path(__file__).with_name("canonical_observation_schema.json")


@lru_cache(maxsize=None)
def load_schema_contract(path: str | Path = DEFAULT_CONTRACT_PATH) -> dict[str, object]:
    """Load the machine-readable canonical observation contract."""

    contract_path = Path(path)
    return json.loads(contract_path.read_text(encoding="utf-8"))


SCHEMA_CONTRACT = load_schema_contract()
CANONICAL_COLUMNS = tuple(field["name"] for field in SCHEMA_CONTRACT["columns"])
OBS_ID_COMPONENT_COLUMNS = tuple(SCHEMA_CONTRACT["identifier"]["components"])
ALLOWED_METHODS = frozenset(SCHEMA_CONTRACT["vocabularies"]["method"]["values"])
SOURCE_KEYS = tuple(SCHEMA_CONTRACT["vocabularies"]["source"]["values"])
QUALITY_FLAG_CODES = tuple(SCHEMA_CONTRACT["vocabularies"]["quality_flags"]["values"])


@dataclass(frozen=True)
class ContractValidationResult:
    """Structured result from canonical schema validation."""

    counts: dict[str, int]
    details: tuple[dict[str, object], ...]

    @property
    def ok(self) -> bool:
        return all(value == 0 for value in self.counts.values())

    def details_frame(self) -> pd.DataFrame:
        return pd.DataFrame.from_records(
            self.details,
            columns=["category", "column", "count", "message"],
        )

    def raise_for_errors(self, context: str = "Canonical observation table") -> None:
        if self.ok:
            return
        messages = "; ".join(str(detail["message"]) for detail in self.details)
        raise ValueError(f"{context} violates the frozen v1.1 schema contract: {messages}")


def stable_scalar_string(value: object) -> str:
    """Serialize a scalar according to the frozen observation-ID contract."""

    if pd.isna(value):
        return ""
    if isinstance(value, (float, np.floating)):
        return format(float(value), SCHEMA_CONTRACT["identifier"]["float_serialization"])
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    return str(value)


def build_cusp_obs_id(df: pd.DataFrame) -> pd.Series:
    """Build deterministic content identifiers using the frozen v1.1 algorithm."""

    separator = str(SCHEMA_CONTRACT["identifier"]["separator"])
    serialized = df.loc[:, OBS_ID_COMPONENT_COLUMNS].apply(
        lambda row: separator.join(
            stable_scalar_string(row[column]) for column in OBS_ID_COMPONENT_COLUMNS
        ),
        axis=1,
    )
    return serialized.map(
        lambda value: f"obs_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]}"
    )


def _text_missing(series: pd.Series) -> pd.Series:
    text = series.astype("string")
    return series.isna() | text.str.strip().eq("").fillna(False)


def _record(
    counts: dict[str, int],
    details: list[dict[str, object]],
    category: str,
    column: str,
    count: int,
    message: str,
) -> None:
    if count <= 0:
        return
    counts[category] += int(count)
    details.append(
        {
            "category": category,
            "column": column,
            "count": int(count),
            "message": message,
        }
    )


def validate_canonical_dataframe(
    df: pd.DataFrame,
    contract: dict[str, object] | None = None,
) -> ContractValidationResult:
    """Validate exact columns, logical types, encodings, IDs, and row rules."""

    contract = contract or SCHEMA_CONTRACT
    fields = contract["columns"]
    expected_columns = [field["name"] for field in fields]
    counts = {
        "column_mismatch": 0,
        "invalid_nullability": 0,
        "invalid_type": 0,
        "invalid_format": 0,
        "invalid_vocabulary": 0,
        "invalid_relationship": 0,
        "identifier_mismatch": 0,
    }
    details: list[dict[str, object]] = []

    if df.columns.tolist() != expected_columns:
        _record(
            counts,
            details,
            "column_mismatch",
            "*",
            1,
            f"Expected columns in order {expected_columns}, got {df.columns.tolist()}.",
        )
        return ContractValidationResult(counts=counts, details=tuple(details))

    numeric: dict[str, pd.Series] = {}
    valid_text: dict[str, pd.Series] = {}

    for field in fields:
        name = str(field["name"])
        logical_type = str(field["type"])
        nullable = bool(field["nullable"])
        series = df[name]

        if logical_type in {"string", "date"}:
            missing = _text_missing(series)
            non_null = ~series.isna()
            non_string = non_null & ~series.map(lambda value: isinstance(value, str))
            valid_text[name] = ~missing & ~non_string
            if not nullable:
                _record(
                    counts,
                    details,
                    "invalid_nullability",
                    name,
                    int(missing.sum()),
                    f"{name} contains {int(missing.sum())} null or blank required values.",
                )
            _record(
                counts,
                details,
                "invalid_type",
                name,
                int(non_string.sum()),
                f"{name} contains {int(non_string.sum())} non-string values.",
            )
            continue

        converted = pd.to_numeric(series, errors="coerce")
        numeric[name] = converted
        non_null = ~series.isna()
        non_finite = converted.notna() & ~converted.map(math.isfinite)
        bad_type = non_null & (converted.isna() | non_finite)
        if not nullable:
            _record(
                counts,
                details,
                "invalid_nullability",
                name,
                int(series.isna().sum()),
                f"{name} contains {int(series.isna().sum())} null required values.",
            )
        _record(
            counts,
            details,
            "invalid_type",
            name,
            int(bad_type.sum()),
            f"{name} contains {int(bad_type.sum())} nonnumeric or nonfinite values.",
        )

        valid_numeric = converted.notna() & ~non_finite
        if logical_type == "integer":
            non_integer = valid_numeric & converted.mod(1).ne(0)
            _record(
                counts,
                details,
                "invalid_type",
                name,
                int(non_integer.sum()),
                f"{name} contains {int(non_integer.sum())} non-integer values.",
            )

        minimum = field.get("minimum")
        if minimum is not None:
            below = valid_numeric & converted.lt(float(minimum))
            _record(
                counts,
                details,
                "invalid_relationship",
                name,
                int(below.sum()),
                f"{name} contains {int(below.sum())} values below {minimum}.",
            )
        maximum = field.get("maximum")
        if maximum is not None:
            above = valid_numeric & converted.gt(float(maximum))
            _record(
                counts,
                details,
                "invalid_relationship",
                name,
                int(above.sum()),
                f"{name} contains {int(above.sum())} values above {maximum}.",
            )
        exclusive_minimum = field.get("exclusive_minimum")
        if exclusive_minimum is not None:
            below_or_equal = valid_numeric & converted.le(float(exclusive_minimum))
            _record(
                counts,
                details,
                "invalid_relationship",
                name,
                int(below_or_equal.sum()),
                f"{name} contains {int(below_or_equal.sum())} values at or below {exclusive_minimum}.",
            )

        allowed_values = field.get("values")
        if allowed_values is not None:
            unsupported = valid_numeric & ~converted.isin(allowed_values)
            _record(
                counts,
                details,
                "invalid_vocabulary",
                name,
                int(unsupported.sum()),
                f"{name} contains {int(unsupported.sum())} values outside {allowed_values}.",
            )

    id_pattern = str(next(field for field in fields if field["name"] == "cusp_obs_id")["pattern"])
    bad_id_format = valid_text["cusp_obs_id"] & ~df["cusp_obs_id"].astype("string").str.fullmatch(id_pattern).fillna(False)
    _record(
        counts,
        details,
        "invalid_format",
        "cusp_obs_id",
        int(bad_id_format.sum()),
        f"cusp_obs_id contains {int(bad_id_format.sum())} values outside the required pattern.",
    )

    date_text = df["date"].astype("string")
    date_shape = date_text.str.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}").fillna(False)
    date_parsed = pd.to_datetime(date_text.where(date_shape), format="%Y-%m-%d", errors="coerce")
    bad_date_format = valid_text["date"] & (~date_shape | date_parsed.isna())
    _record(
        counts,
        details,
        "invalid_format",
        "date",
        int(bad_date_format.sum()),
        f"date contains {int(bad_date_format.sum())} values outside valid YYYY-MM-DD dates.",
    )

    for field in fields:
        vocabulary_name = field.get("vocabulary")
        if vocabulary_name in {None, "quality_flags"}:
            continue
        name = str(field["name"])
        allowed_values = set(contract["vocabularies"][vocabulary_name]["values"])
        unsupported = valid_text[name] & ~df[name].isin(allowed_values)
        _record(
            counts,
            details,
            "invalid_vocabulary",
            name,
            int(unsupported.sum()),
            f"{name} contains {int(unsupported.sum())} unsupported codes.",
        )

    quality_field = next(field for field in fields if field["name"] == "quality_flags")
    quality_text = df["quality_flags"].astype("string")
    quality_nonempty = valid_text["quality_flags"]
    quality_pattern = str(quality_field["pattern"])
    malformed_flags = quality_nonempty & ~quality_text.str.fullmatch(quality_pattern).fillna(False)
    _record(
        counts,
        details,
        "invalid_format",
        "quality_flags",
        int(malformed_flags.sum()),
        f"quality_flags contains {int(malformed_flags.sum())} malformed strings.",
    )

    allowed_flags = list(contract["vocabularies"]["quality_flags"]["values"])
    flag_order = {code: position for position, code in enumerate(allowed_flags)}
    unknown_flag_rows = 0
    duplicate_flag_rows = 0
    unordered_flag_rows = 0
    parseable_flags = quality_nonempty & ~malformed_flags
    for value in quality_text.loc[parseable_flags]:
        codes = str(value).split(";")
        unknown = [code for code in codes if code not in flag_order]
        if unknown:
            unknown_flag_rows += 1
            continue
        if len(codes) != len(set(codes)):
            duplicate_flag_rows += 1
        if codes != sorted(codes, key=flag_order.__getitem__):
            unordered_flag_rows += 1
    _record(
        counts,
        details,
        "invalid_vocabulary",
        "quality_flags",
        unknown_flag_rows,
        f"quality_flags contains {unknown_flag_rows} rows with undefined codes.",
    )
    _record(
        counts,
        details,
        "invalid_format",
        "quality_flags",
        duplicate_flag_rows,
        f"quality_flags contains {duplicate_flag_rows} rows with duplicate codes.",
    )
    _record(
        counts,
        details,
        "invalid_format",
        "quality_flags",
        unordered_flag_rows,
        f"quality_flags contains {unordered_flag_rows} rows outside canonical code order.",
    )

    expected_ids = build_cusp_obs_id(df)
    id_mismatch = valid_text["cusp_obs_id"] & df["cusp_obs_id"].astype("string").ne(expected_ids)
    _record(
        counts,
        details,
        "identifier_mismatch",
        "cusp_obs_id",
        int(id_mismatch.sum()),
        f"cusp_obs_id differs from the frozen content hash for {int(id_mismatch.sum())} rows.",
    )
    duplicate_ids = df["cusp_obs_id"].notna() & df["cusp_obs_id"].duplicated(keep=False)
    _record(
        counts,
        details,
        "identifier_mismatch",
        "cusp_obs_id",
        int(duplicate_ids.sum()),
        f"cusp_obs_id is duplicated on {int(duplicate_ids.sum())} rows.",
    )

    pf_observed = numeric["pf_observed"]
    thaw_depth = numeric["thaw_depth"]
    pf_depth = numeric["pf_depth"]
    obs_limit = numeric["obs_limit"]
    flag_sets = quality_text.fillna("").map(lambda value: set(str(value).split(";")) - {""})
    visual = flag_sets.map(lambda codes: "VI" in codes)
    upper_bound = flag_sets.map(lambda codes: "UB" in codes)
    absence = pf_observed.eq(0)
    presence = pf_observed.eq(1)

    absence_depth = absence & (thaw_depth.notna() | pf_depth.notna())
    _record(
        counts,
        details,
        "invalid_relationship",
        "thaw_depth,pf_depth",
        int(absence_depth.sum()),
        f"{int(absence_depth.sum())} absence rows claim a canonical depth.",
    )
    unbounded_absence = absence & ~visual & obs_limit.isna()
    _record(
        counts,
        details,
        "invalid_relationship",
        "obs_limit",
        int(unbounded_absence.sum()),
        f"{int(unbounded_absence.sum())} nonvisual absence rows lack obs_limit.",
    )
    depthless_presence = presence & thaw_depth.isna() & pf_depth.isna() & ~upper_bound
    _record(
        counts,
        details,
        "invalid_relationship",
        "thaw_depth,pf_depth",
        int(depthless_presence.sum()),
        f"{int(depthless_presence.sum())} unflagged presence rows lack a depth.",
    )
    thaw_beyond_limit = thaw_depth.notna() & obs_limit.notna() & thaw_depth.gt(obs_limit)
    pf_beyond_limit = pf_depth.notna() & obs_limit.notna() & pf_depth.gt(obs_limit)
    thaw_beyond_pf = thaw_depth.notna() & pf_depth.notna() & thaw_depth.gt(pf_depth)
    for column, mask, message in (
        ("thaw_depth", thaw_beyond_limit, "thaw_depth exceeds obs_limit"),
        ("pf_depth", pf_beyond_limit, "pf_depth exceeds obs_limit"),
        ("thaw_depth,pf_depth", thaw_beyond_pf, "thaw_depth exceeds pf_depth"),
    ):
        _record(
            counts,
            details,
            "invalid_relationship",
            column,
            int(mask.sum()),
            f"{int(mask.sum())} rows have {message}.",
        )

    return ContractValidationResult(counts=counts, details=tuple(details))


def quality_flag_vocabulary_matches(path: str | Path) -> bool:
    """Return whether the maintained flag table matches the contract vocabulary."""

    definitions = pd.read_csv(path)
    return definitions["flag_code"].astype(str).tolist() == list(QUALITY_FLAG_CODES)
