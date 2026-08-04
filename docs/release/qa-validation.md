# Formal QA Validation

This page records the current QA layer and the latest validated result for the
canonical CUSP observation table.

## QA Workflow

Hard-gate checks run with:

```bash
python -m cusp.qc validate-observations --out outputs/qc_tests
```

They require:

- the exact canonical observation schema
- present and unique `cusp_obs_id`
- binary `pf_observed`
- supported direct-observation `method` values
- present and valid coordinates
- parseable and in-range dates
- nonnegative depth values
- no zero observation limits

The diagnostic audit runs with:

```bash
python -m cusp.qc audit-observations --out outputs/qc_audit
```

It writes review files without changing the observations.

## Latest Result

Validated on 2026-08-04 under Python 3.12:

- hard-gate status: passed
- canonical table: `77,916` rows and `13` columns
- complete test suite: `50 passed`
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

- presence: `60,872`
- absence to a positive observation limit: `17,044`

## Build-Enforced Semantics

The observation build also rejects any absence without a positive
`obs_limit`. It clears canonical depth fields on absence rows, adds `LB` to
bounded absences, and adds `UB` to presence rows whose exact depth is unknown.

These rules supplement the general QA checks because they encode CUSP's
observation semantics rather than generic numeric validity.

## Nonblocking Checks

Missing `site_id`, source-specific overlap notes, and the
`thaw_depth > pf_depth` check remain diagnostic. They are exposed for review
but do not automatically invalidate otherwise usable observations.
