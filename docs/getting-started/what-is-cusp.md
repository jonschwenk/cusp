# What CUSP Is

CUSP is the CommUnity near-Surface Permafrost data synthesis. It brings
near-surface permafrost observations from many source datasets into a shared,
documented table.

## What It Contains

CUSP focuses on observations that can support rows in the main release table:

- permafrost presence or absence
- active-layer thickness
- thaw depth or frost-table depth
- depth to permafrost
- observation location, date, method, and source provenance

The main table is intentionally compact. It is meant to be stable enough for
analysis, release comparison, and reproducible downstream work.

## What It Is Not

CUSP is not a global permafrost map, a model output archive, or a complete copy
of every source dataset. It keeps the common information that can be compared
across sources and preserves source citations so users can go back to the
original records when needed.

Some users may create spatial summaries or add environmental information from
external datasets. Those are useful extensions, but the starting point is the
main CUSP table.

## Why Observation Level Matters

Keeping individual observations visible makes it easier to:

- trace each row back to its source
- update or defer individual sources as evidence improves
- keep derived products reproducible
- cite both CUSP and the underlying datasets responsibly
