# CUSP Agent Instructions

Before discovering, evaluating, or ingesting a dataset, read and follow
[`agents/dataset-ingestion.md`](agents/dataset-ingestion.md).

The maintainer decides whether a source belongs in CUSP and whether it may be
released. Agents may investigate candidates and implement complete ingestions,
but must leave new sources at `release_clearance = "needs_review"` until a
maintainer explicitly changes that status.

Repository documentation and the canonical schema remain authoritative. Work
with existing user changes, keep source-specific assumptions explicit, and do
not use broad proximity-based deduplication to remove scientifically meaningful
repeat observations.
