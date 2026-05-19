# Formal QA Validation

This document records the current QA layer for the canonical
observation-level release bundle and the latest audited state of that layer.

## QA Workflow

Hard-gate tests live in [tests/test_qc_observations.py](https://github.com/jonschwenk/cusp/blob/main/tests/test_qc_observations.py).
They validate the working observation table before it is exported as
`cusp_vX.Y.csv`:

- exact canonical observation columns only
- present and unique `cusp_obs_id`
- valid binary `pf_observed`
- supported direct-observation `method` values
- no missing or out-of-range coordinates
- parseable and in-range dates
- no negative depth values
- no `obs_limit == 0`

Diagnostic audits are available through `python -m cusp.qc audit-observations`
and the shared helpers in [cusp/qc](https://github.com/jonschwenk/cusp/blob/main/cusp/qc).
The audit is intentionally behind-the-scenes: it writes review outputs under
`outputs/qc_audit/` and does not mutate data.

## Current result

Latest run:

- `python -m unittest tests.test_qc_observations tests.test_build tests.test_aggregate tests.test_process_script_metadata`
- `python -m cusp.qc audit-observations --input <working-observation-table> --out outputs/qc_audit`

Observed outcome:

- all hard-gate tests passed
- current canonical observation table size: `239,704` rows
- current canonical observation table columns: `11`
- no hard-gate failures were written to `outputs/qc_tests/`

## Current audit summary

From `outputs/qc_audit/qc_summary.json`:

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
- unsupported method rows: `0`
- `n_thaw_gt_pf_diagnostic = 53`
- `n_suspect_swapped_latlon = 0`

Current `pf_observed` counts in the canonical observation table:

- `1`: `230,430`
- `0`: `9,274`

## Explicit non-blockers

The following are intentionally *not* part of the hard-gate observation QA:

- missing `site_id`
- duplicate-heavy source semantics that remain source-level review topics
- below-Arctic-circle checks

Those may still be reviewed manually or through source-specific triage, but
they do not currently block the canonical release build.

## Still deferred

These QA topics are still open for future refinement rather than implemented as
formal blockers today:

- ocean / impossible-location screening
- stronger intended-domain checks
- source-specific duplicate semantics beyond current build-level exact-duplicate handling
