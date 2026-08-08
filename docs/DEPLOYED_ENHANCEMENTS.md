# Downloaded original to current NscaleTX deployment

The exact source-level record is the Git diff from
`downloaded-original-sanitized-20260605` to `main`. This document groups the
changes by operator-visible capability; it is not a substitute for that diff.

The exhaustive export inventory in `original-to-current-files.csv` contains
308 added files, 113 modified files, 6 removed files, and 228 unchanged files.
That count includes the handoff documents and credential-free compose example
added during packaging. Runtime state, deployment secrets, generated assets,
caches, and local backups are not counted.

## Cluster execution and platform model

- Added a catalog for projects, clusters, hardware platforms, tools, naming,
  connection endpoints, and role-based placement.
- Replaced direct local assumptions with composable local/SSH transport,
  multi-hop topology, host-side filesystem operations, and BCM/MAAS provider
  abstractions.
- Added production drift detection and checksum-based deployment of remote
  scripts so head-node fixes are discovered before deployment.
- Expanded NVIS naming, rack/node mapping, Slurm command handling, scheduler
  adapters, advisory rack locks, and job environment overrides.
- Added the 15-minute default cache for slow-changing BCM rack inventory while
  retaining normal refresh cadence for device state, Slurm, logs, and metrics.

## Rack, node, and fleet views

- Added progressive cluster status loading and resilient cached snapshots.
- Added the Nodes view with per-node bring-up results, node detail, live
  refresh, cluster heatmaps, sortable/filterable node tables, and report
  export. The downloaded original exposed rack-level views only.
- Added live cluster overview sections, node-report schema validation, recent
  jobs, floor/rack views, status explanations, pagination, filters, and direct
  links between analytics rows and node details.
- Corrected false stage failures, stale-log precedence, partial NCCL tables,
  placeholder parser rows, and per-run chart selection.

## Validation and workload orchestration

- Added durable validation activities with task-level Slurm state and output
  discovery, while retaining the existing live async polling interface.
- Added single- and multi-rack NCCL/NeMo/LLMB controls, launch options,
  NVLink preflight, multi-rack filters, stage selection, and NeMo step count.
- Added or revised NCCL, NeMo, MNUBERGEMM, NVLoom, ClusterKit, sysinfo,
  health-check, collection, and image/workspace scripts.
- Added automatic LLMB result collectors and fixed missing collection when a
  readable collector lacked its execute bit.
- Added parser completeness gates, shared rack/log classification helpers,
  and tests for concurrency, cache merging, stage attribution, and launch
  configuration.

## History, Parquet, and observability

- Added universal log parsing and SQLite result history, including capture of
  attempts that fail before producing an application log.
- Added the Parquet lake sink for parsed results, background actions, and
  Rack Status API action/request evidence.
- Added native VictoriaMetrics queries and Chart.js panels for GPU,
  infrastructure, and event telemetry, replacing most Grafana iframe views
  while retaining scoped Grafana deep-links.
- Added node-level analytics and cluster/rack/node scope throughout the
  VictoriaMetrics integration.
- Added Grafana link helpers, lake health, run history, and parser-result
  architecture documentation.

## Frontend, packaging, and operations

- Added the project/cluster switcher, platform and tool administration,
  workflow composition, launch progress, validation activities, node detail,
  accessibility, pagination, and KUI component migrations.
- Vendored Kaizen CSS/fonts for air-gapped use and added offline Docker-image
  bundle support.
- Expanded GitLab CI to lint and test Python/TypeScript and build the image.
- Added NscaleTX deployment, networking, NCCL, bring-up, IMEX, power-cap,
  parser, and validation documentation.

## Known retained debt

- The deployed compose override is instance-specific and is intentionally not
  in Git. Use the supplied example plus an ignored local environment.
- Some legacy Grafana embed code is retained although deep-links and native
  VictoriaMetrics panels are the preferred paths.
- The SQLite history can contain multiple growth snapshots and duplicate
  parser-path records. It is preserved unchanged pending an explicit data
  retention/deduplication decision.
- A completed async job is only directly joined to its numeric Slurm ID after
  collector/output discovery. The Parquet reconciliation document describes
  the resulting audit gap.
