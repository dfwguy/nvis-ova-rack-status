# Rollback and later PythonCM cutover

PythonCM is not implemented in this export. The purpose of this checkpoint is
to make that rework low-risk.

## Deployment shape

Keep the current cmsh-backed service, source tree, Docker image, and live data
volume intact. Build PythonCM as a separate backend adapter and run it as a
read-only shadow/canary on a different local port. It must not launch, cancel,
drain, undrain, reboot, reset, or edit BCM objects while shadowing.

The canary should use:

- one persistent authenticated connection;
- server-side filtering;
- cached inventory and identity maps;
- incremental/delta updates where the BCM API supports them;
- in-memory UI responses; and
- independent refresh queues for inventory, Slurm, logs, and telemetry.

Validation scripts and Slurm jobs continue to run on the head node exactly as
today. Replacing the inventory/status read path does not require changing those
scripts. Action endpoints stay on the current implementation until read parity
has been demonstrated and each mutating call has a separately reviewed API
mapping.

## Parity gates

Compare both backends over multiple launch windows, not a single response:

1. rack and node inventory cardinality and identities;
2. BCM power/device state and Slurm state;
3. per-stage job/log attribution;
4. rack and node status summaries;
5. latency, CMDaemon calls, head-node CPU, memory, NFS RPCs, and I/O;
6. stale/error behavior when BCM, Slurm, VictoriaMetrics, or the head node is
   temporarily unavailable; and
7. zero differences in the preserved SQLite/Parquet history contracts.

Only move user traffic after sustained parity. Keep the old container warm or
startable from the captured image. Rollback changes the routing/container, not
the database: reuse the current volume so history collected after this
snapshot is not lost.

## Historical data and UI behavior

SQLite, Parquet, VictoriaMetrics, and the frontend API schemas remain outside
the BCM adapter. The PythonCM rework is therefore under the hood if the adapter
contract is kept stable. Existing historical rows do not need migration. Add
schema/version fields only for genuinely new data; never rewrite old verdicts
as part of the transport change.

