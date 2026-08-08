# Pre-PythonCM checkpoint test report — 2026-08-08

This report describes validation performed against the GitLab-ready checkpoint on
the ObsVM. No Slurm jobs were launched, cancelled, requeued, or otherwise changed.

## Backend suite

The isolated backend suite was run in demo/local execution mode so tests could not
reach the production Slurm control path:

```text
911 passed, 2 skipped, 3 failed in 310.72s
```

The three failures were investigated individually:

1. `TestContext::test_switch_changes_geometry_and_compat` passed when rerun alone.
   It is sensitive to global fixture/order state in the complete suite.
2. `test_a_fleet_with_no_results_cannot_be_a_valid_report` passed once the declared
   `jsonschema` dependency was available. The existing source virtual environment
   did not contain that dependency; `backend/requirements.txt` and GitLab CI do.
3. `test_selected_nodes_scope_the_run` passed when rerun alone. In the complete
   suite its asynchronous test worker did not reach a terminal state within the
   test's ten-second deadline.

The new BCM rack-inventory cache tests passed independently:

```text
3 passed in 0.05s
```

These results identify two full-suite isolation/timing debts and one stale local
virtual environment; they do not indicate a reproducible product failure in the
three affected paths.

## Static and package checks

- Python bytecode compilation completed successfully.
- `scripts/compare_snapshot_trees.py` passes Ruff.
- `git diff --check` reports two inherited blank-lines-at-EOF findings in
  `backend/app.py` and `frontend/src/components/rack/NodeSelector.tsx`. They are
  preserved to keep the checkpoint byte-for-byte aligned with deployed source.
- `backend/native_status.py` retains 11 pre-existing Ruff findings. This checkpoint
  intentionally preserves deployed source rather than mixing cleanup into the
  rollback baseline.
- The sanitized compose example renders successfully with placeholder environment
  values.
- `scripts/check_no_vault_in_git.sh` passes.
- Scans found no private-key blocks, GitLab personal tokens, AWS access-key IDs, or
  prohibited secret files in the export. Literal token/password strings that remain
  are test fixtures; the only non-test token-named constant is an HTTPS endpoint.
- Frontend tests were not run on the ObsVM because Node/npm dependencies are not
  installed locally. The included GitLab pipeline installs them before testing.

## Runtime checks

- The deployed RackStatus HTTP endpoint continued to return its expected redirect
  after the snapshot.
- Both online SQLite backup copies pass `PRAGMA integrity_check`.
- The exact deployed Docker image was saved and checksummed in the private rollback
  snapshot described by `docs/ROLLBACK_AND_PYTHONCM_CUTOVER.md`.
