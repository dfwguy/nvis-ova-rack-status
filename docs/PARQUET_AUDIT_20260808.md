# Parquet run-capture audit — 2026-08-08

Audit time was approximately 19:00 UTC on the ObsVM.

## What is healthy

- `nvis-lakewriter` health returned HTTP 200.
- The 2026-08-08 NscaleTX `run_artifacts` partition contained 339 readable
  Parquet files and 678 rows at the 19:00 audit boundary; all files opened
  without error.
- The partition held both `run_log` and `parsed_result` rows for Rack Status
  request/action evidence.
- Captures ranged from 00:57:58 through 16:13:39 UTC. The final two records
  were login requests; no lake writer error was found after that time.
- Rack Status was configured with `RACK_LAKE_CAPTURE=actions`, so ordinary
  polling is intentionally excluded.

The six live NCCL racks all have launch-request evidence in Parquet: E03, E15,
F01, F08, F20, and G03. Their numeric Slurm jobs were `132603`, `132597`,
`132598`, `132490`, `132494`, and `132500`; they remained running at audit
time, so terminal result artifacts were not expected yet.

## What is not yet auditable end to end

The launch request row is created before the async worker learns the Slurm job
number. It is keyed by a request/activity UUID. Until the collector finishes,
there is no durable direct join from that launch row to its numeric Slurm ID.
This means the lake proves the Rack Status click occurred but does not yet
prove, by indexed fields alone, which scheduler allocation it created.

Only a small subset of today's completed numeric result logs was present as a
job-keyed parsed result at audit time (including `132328`, `132393`, `132396`,
`132473`, `132477`, and `132630`). Direct Slurm/ClusterKit submissions are not
universally captured by the Rack Status request hook. Therefore the statement
"every recent test is in Parquet" is not currently supportable.

## Required closure before PythonCM cutover

- Persist the scheduler ID into the activity/lake row immediately when submit
  returns, independent of final log collection.
- Add a low-rate `sacct` reconciliation job that compares relevant completed
  allocations with job-keyed lake artifacts and backfills missing attempts,
  including jobs that produce no application log.
- Record submit source (`rackstatus`, ObsVM CLI, head CLI, external) and the
  immutable source log path.
- Alert on completed jobs lacking a terminal artifact after a grace period.
- Keep reconciliation off the interactive request path and cache accounting
  reads so coverage does not increase head-node load materially.

No Parquet files were changed or backfilled during this audit.

## Live refresh at 19:25 UTC

Four subsequent Rack Status actions brought the partition to 343 readable
files and 686 rows. They included login/preset reads and a complete E02 NVLink
preflight request/result pair, confirming that the action sink continued to
write successfully while this checkpoint was built. Numeric Slurm job `133128`,
which completed at 19:24:31 UTC, was not present in any artifact field or
content at that time, consistent with the direct-submission/reconciliation gap
above.
