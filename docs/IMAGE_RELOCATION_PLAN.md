# Validation image relocation to the observability VM

No image was moved while this export was prepared. Six live 16-18-node NCCL
jobs were still reading the current head-node path, so copying tens or hundreds
of GiB from head-node NFS would have added avoidable pressure.

## Verified inventory and topology

- ObsVM `/data`: about 7 TiB total and 6.3 TiB free at audit time.
- ObsVM NFS server: active and enabled.
- Current export: `/data/llmb-scratch` to `10.40.0.0/16`.
- Head `/data/llmb/images`:
  - `nvidia+nemo+26.02.01.sqsh` — 43,259,932,672 bytes;
  - `nvidia+nemo+26.04.00.sqsh` — 42,150,760,448 bytes.
- Head `/data/llmb/workloads/microbenchmark_cpu_overhead/gpt-oss-120b`
  contains 37 files and about 195.8 GB apparent size. It includes the
  downloaded model shards and converted model object associated with the
  incomplete Exemplar/LLMB work. Preserve this directory as resumable workload
  state; do not relabel it as a container image.
- Head `/data/llmb/workloads/microbenchmark_nccl` is about 29.5 GB apparent
  size, primarily the Exemplar NCCL repository, environments, and experiment
  artifacts.
- The active shared workspace image directory was inventoried metadata-only as
  UID `cmods` through the ObsVM's NFS mount. It contains:
  - `nvidia+nemo+26.04.01.sqsh` — 42,245,001,216 bytes;
  - `tensorrt-llm+release+1.1.0rc5.sqsh` — 30,284,881,920 bytes.
- Active LLMB/NCCL jobs use `nvidia+nemo+26.04.01.sqsh`. This was verified from
  a running rank's command line. The TensorRT-LLM image is inventoried but is
  not assumed to be part of the requested NCCL/NeMo move without a consumer
  check.
- The NCCL benchmark itself is workload code/binaries plus experiment
  artifacts; it is not a separate large `.sqsh` under head `/data`.
- A distinct partial Exemplar `.sqsh` was not found. Exemplar is the
  `dgxc-benchmarking`/LLMB toolchain here; its large partial state is workload
  and model data, not a third image file. Metadata confirms the shared
  workspace has both `microbenchmark_nccl` and
  `microbenchmark_cpu_overhead/gpt-oss-120b`; content checksums remain gated
  until the live jobs finish.

The previous attempt to move the shared image directory from head `/home` to
head-local `/data` broke every compute-node path because `/data` was not
exported. A symlink does not cross that boundary. The ObsVM migration must use
a real compute-node NFS mount and must be verified from consumers.

## Safe sequence

1. Wait for all jobs using the source image path to leave RUNNING/COMPLETING.
2. As `cmods`, inventory `/home/cmods/workspace/llmb/images` and the Exemplar
   download locations with byte size, mtime, and SHA-256. Record partial-file
   names separately.
3. Create `/data/llmb-scratch/images` on the ObsVM with an explicit owner/group
   and non-world-writable permissions. Do not use the current top-level sticky
   directory as the final permission model.
4. Copy; never move or delete the source. Preserve partial downloads as
   partial objects. Use resumable transfer and rate limiting if the head is
   serving other work.
5. Verify source and destination size and SHA-256.
6. Mount the ObsVM export at the same explicit path on one idle compute node.
   Verify file visibility and a read-only checksum from that node.
7. Mount through the supported BCM/category mechanism, then verify every node
   selected for the first canary. Reachability to TCP/NFS is not proof that the
   filesystem is mounted or usable.
8. Run one operator-launched validation canary using the new absolute path.
   Compare launch time, NFS RPC latency, retries/timeouts, head and ObsVM I/O,
   and the final Parquet record.
9. Point only new jobs at the new location. Existing jobs retain their old
   path. Keep the head copies until multiple NCCL and NeMo validations pass and
   rollback has been exercised.

Do not replace `/home/cmods/workspace/llmb/images` with a symlink. Use explicit
configuration for the new mount so rollback is a configuration reversal.
