# Formal QA Validation

This page records the current QA layer and the latest validated result for the
canonical CUSP observation table.

## QA Workflow

Hard-gate checks run with:

```bash
python -m cusp.qc validate-observations --out outputs/qc_tests
```

They require:

- the exact frozen column names and order
- contract-compliant logical types, nullability, units, and encodings
- present, unique, correctly formatted, and deterministically reproduced
  `cusp_obs_id`
- binary `pf_observed`
- registered source keys and supported `method` values
- well-formed, defined, deduplicated, canonically ordered quality flags
- present and valid coordinates
- valid `YYYY-MM-DD` dates in the supported range
- nonnegative depth values
- no zero observation limits
- valid presence, absence, depth, observation-limit, `UB`, and `VI`
  relationships

The machine-readable source of truth is
`cusp/canonical_observation_schema.json`. The build, exporter, QA command, and
test suite all load the same contract.

The diagnostic audit runs with:

```bash
python -m cusp.qc audit-observations --out outputs/qc_audit
```

It writes review files without changing the observations.

## Latest Result

Validated on 2026-08-25 under Python 3.13:

- hard-gate status: passed
- canonical table: `79,389` rows and `12` columns
- complete test suite: `74 passed` with `26` passing subtests
- processing metadata: `57` structured headers, `0` validation errors
- build-level QC flag log: `0` rows

## Audit Summary

- `n_missing_cusp_obs_id = 0`
- `n_duplicate_cusp_obs_id = 0`
- `n_date_unparseable = 0`
- `n_date_future = 0`
- `n_date_too_old = 0`
- `n_missing_xy = 0`
- `n_invalid_xy_range = 0`
- `n_negative_pf_depth = 0`
- `n_negative_thaw_depth = 0`
- `n_negative_obs_limit = 0`
- `n_zero_obs_limit = 0`
- `n_invalid_pf_observed = 0`
- `n_thaw_gt_pf_diagnostic = 0`
- `n_suspect_swapped_latlon = 0`

Current `pf_observed` counts:

- presence: `62,135`
- absence: `17,254`, comprising `17,054` depth-bounded records and `200`
  flagged visual Koyukuk classifications without a point-specific limit

## Build-Enforced Semantics

The observation build rejects any instrument-based absence without a positive
`obs_limit`. It permits a blank limit only for a row explicitly marked as a
visual interpretation (`VI`), and still rejects zero or negative limits. It
clears canonical depth fields on absence rows, adds `LB` to bounded absences,
and adds `UB` to presence rows whose exact depth is unknown.

These rules supplement the general QA checks because they encode CUSP's
observation semantics rather than generic numeric validity.

## Nonblocking Checks

Missing `site_id`, source-specific overlap notes, and the
`thaw_depth > pf_depth` check remain diagnostic. They are exposed for review
but do not automatically invalidate otherwise usable observations.
