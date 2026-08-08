# Prior Claude documentation inventory

The migration audit used the prior handovers and mistake logs as evidence,
then checked their claims against the running system. Documentation is not
silently treated as current truth where live state differs.

## Operational handover set

- `/opt/observability/claudeisanidiot/README.md`
- `HANDOVER_TO_CODEX.md`
- `HANDOFF_TO_CODEX_2026-08-07.md`
- `WORKING_PROTOCOL.md`
- `FUCKUPS_2026-08-06_DASHBOARDS_AND_FLEET.md`
- `FUCKUPS_2026-08-07_TELEMETRY_AND_MISREADS.md`
- `FUCKUP_2026-08-05_LLMB_IMAGES_MOVED_TO_LOCAL_DATA.md`
- `FUCKUP_2026-08-08_WRONG_SERVICE_ON_4213.md`
- `INCIDENT_2026-08-06_SU1-SU2_NCCL_SCANCEL.md`

The most relevant durable lessons for this migration are: do not fire jobs;
verify filesystems from a compute consumer; treat blank reads as failures;
preserve head-node scripts and production drift; do not equate lake health
with complete run coverage; and remember that Docker file bind mounts remain
attached to an old inode after atomic editor replacement until container
recreation/restart.

## Current tool documentation

- `docs/NSCALE_TX_DEPLOYMENT.md`
- `docs/PARSING_RESULTS_ARCHITECTURE.md`
- `docs/EXECUTION_ARCHITECTURE.md`
- `docs/GRAFANA_PROMETHEUS_INTEGRATION.md`
- `docs/BRINGUP_AUTOMATION_INTEGRATION.md`
- the NCCL, LLMB, IMEX, power-cap, Slurm containment, and validation runbooks
  under `docs/`.

## OVA documentation set

The separately assembled operator set under
`/opt/observability/nvis-ova-rack-status/docs/` contains:

1. what the distribution is;
2. prerequisites;
3. quick start;
4. configuration reference;
5. cluster profile;
6. VictoriaMetrics;
7. Grafana;
8. exporters;
9. Parquet data lake;
10. validation runbook;
11. LLMB/Exemplar;
12. analytics/reports;
13. troubleshooting;
14. known issues/pitfalls;
15. architecture;
16. security; and
17. upgrading.

These documents describe a broader OVA distribution than the one Rack Status
container. Their topology, credentials, ports, and current service assertions
must be verified against the live ObsVM before use. Secret-bearing staging
inputs and Claude credential/session files were deliberately excluded from
the GitLab export.

