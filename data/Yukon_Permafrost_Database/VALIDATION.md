# Staging validation, 2026-11-03

Environment: Miniforge `cusp`, Python 3.13.18. Release clearance remains
`needs_review`. No official export or archive was rebuilt.

Passed:

- Offline processor rerun with pinned inputs and exact tier-count assertions.
- Strict generated process metadata: 61 structured sources, zero errors.
- Canonical build and QC: **81,237 rows**, zero schema/value/relationship errors.
- 30 m aggregation and membership QC: **36,187 rows**, zero reported errors.
- Full tests: **133 passed, 1 skipped, 167 subtests passed**. The skip is the
  existing Windows exclusion for Bash syntax validation.
- Strict MkDocs build, published README tracker check, and Git whitespace check.
- Reproducible overlap screening scripts, excluding the new source from its own
  comparison inputs; no provenance-supported duplicate removal found.

The new focused suite has 24 cases covering interval semantics, negative and
uncertain text, summer versus winter inference, bounded non-detections,
coordinate fallback, temperature coverage/margin/provider continuity, pinned
counts, and deterministic CSV serialization. Pytest plugin autoload was disabled
for these runs; the core subtest support remained active.

The test harness used PATH rather than full Conda activation, producing two
GDAL data-path warnings concerning an optional New Zealand tile-matrix JSON.
The tests and GIS writes passed. Normal `conda activate cusp` supplies the GDAL
environment hooks; no dataset or GIS-library code was changed to suppress warnings.

## Reproducibility repair

The first final byte comparison caught unordered quality-flag CSV columns.
Serialization now orders canonical fields explicitly and all remaining fields
lexically; the added regression test checks insertion-order independence.
Two fresh processor executions with `PYTHONHASHSEED=11` and `23` produced the
same generated CSV SHA-256:

`98d16f38d96376b2b7d7afc86f3616034ea86c03713be3d75484049878aa94a2`

Rebuilding after the serialization repair left canonical CSV bytes unchanged:

`0fbbdc2d34fc35c9cab9ce7a0b1d3afeeb3bb3dd3c77165352f2391669dc3299`

The full suite was rerun after the repair and passed with the final counts above.
Aggregation/QC inputs were byte-identical, so those already-passing checks were
not repeated unnecessarily. Provider CSV/compact thermal evidence uses Git
`-text` attributes so input hashes survive checkout on Windows and Linux.

Detailed local logs are in ignored `runs/yukon_stage_validation/`; original
source and scientific/overlap investigations are in
`runs/yukon_candidate_20261103/`. See README for the versioned reproduction scripts.
