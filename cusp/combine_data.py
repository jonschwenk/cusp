"""Compatibility wrapper for the observation build pipeline.

The supported observation-level assembly path now lives in `cusp.build`.
This module remains so older references to `cusp/combine_data.py` keep working
while the repo transitions to the single `build.py` entry point.
"""

from cusp.build import (
    BuildOutputs,
    apply_hard_deletions,
    build_metastats,
    build_qc_flags,
    build_release_metadata,
    build_release_tables,
    combine_sources,
    ensure_release_columns,
    list_available_sources,
    list_included_sources,
    load_processed_source,
    main,
    normalize_method,
    normalize_methods,
    stable_allfields_column_order,
    validate_data_df,
    write_build_outputs,
)

__all__ = [
    "BuildOutputs",
    "apply_hard_deletions",
    "build_metastats",
    "build_qc_flags",
    "build_release_metadata",
    "build_release_tables",
    "combine_sources",
    "ensure_release_columns",
    "list_available_sources",
    "list_included_sources",
    "load_processed_source",
    "main",
    "normalize_method",
    "normalize_methods",
    "stable_allfields_column_order",
    "validate_data_df",
    "write_build_outputs",
]


if __name__ == "__main__":
    main()
