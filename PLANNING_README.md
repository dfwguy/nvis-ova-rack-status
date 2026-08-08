# NVIS Rack Status — Planning & Deployment README (NscaleTX GB300 SuperPOD ObsVM)

**Component:** `nvis-rack-status` v0.1.3
**Target host:** NscaleTX GB300 SuperPOD **ObsVM** (`network-server`, dual-homed `192.168.10.3` mgmt + `10.40.x` fabric)
**Deployed on host port:** `5055` → container `5000`
**Container name:** `nvis-rack-status`
**Role:** The **active** bring-up / validation / remediation console layered on top of the existing **passive** 29-container observability stack.

> This document is the operator-facing plan for running the tool on the ObsVM. It is grounded in the four upstream analyses (features/architecture/deploy/validation-fit) plus the repo's own `README.md`, `INSTALL.md`, `docs/`, `Dockerfile`, `docker-compose.yml`, `build-docker.sh`, and `start.sh`.

---

## 1. Overview — What It Is

`nvis-rack-status` is a **full-stack rack validation and operations platform** for NVIDIA GB200/GB300 GPU clusters. It combines:

- a **Flask** backend (single ~13k-line `backend/app.py`, ~120 REST routes + SSE + a WebSocket PTY middleware), and
- a compiled **React 19 / TypeScript** single-page app (NVIDIA Kaizen UI + MUI, Chart.js, React Flow, xterm.js, mermaid),

packaged as **one Docker container**.

Crucially, it is **not** a telemetry collector. It has **no** direct BMC/Redfish, SNMP, IPMI, or database polling. Its data source is **command execution on a cluster head node**: it runs `cmsh` (BCM) or `maas-cli` (MAAS), Slurm CLI (`sinfo`/`squeue`/`sacct`/`scontrol`), `pdsh`, and a bundled `bin/scripts/` toolkit, then parses NEMO/NCCL validation logs. It is the layer that **drives** the acceptance test plan and **remediates** faults — the one capability the passive VictoriaMetrics/Grafana/Loki/exporter stack does not have.

State is **flat files on disk** (JSON/YAML under `var/`) — there is no database.

---

## 2. Features & Data

**Rack operations dashboard**
- Sortable per-rack status table: validation state (`done` / `fail` / `ongoing[elapsed]` / `pending`) + human-readable failure hints (e.g. "NCCL busbw below threshold", "LLM did not reach target steps").
- Live rack/tray readiness board: BCM `cmsh rack;list` + `ds` rendered as UP / DOWN / INST tray blobs, merged with Slurm `sinfo` state counts and the last Slurm job id.
- Parser charts: NCCL all-reduce bus-bandwidth, step-time, NVLoom heatmaps, ClusterKit results, fleet-median deviation aggregation.
- Multirack validation view with aggregate analysis.
- Log export to **Excel/CSV/zip**, real-time log streaming (`tail -f` over SSE), and `nvidia-bug-report` bundle collection.
- Optional embedded **Grafana** solo panels (GPU thermal/power) via iframe.

**Validation-workload orchestration** (unique to this tool)
- Launches NEMO single-rack, cross-rack NEMO, single-node Llama, MNUberGEMM burn-in, NVLoom, ClusterKit, DCGM/`checker.sh` hw presets, NVSwitch rack audit, and `sysinfo` firmware/FRU capture — all via SSH → BCM head + Slurm.

**Remediation actuation** (no equivalent in the stack)
- `gpu-reset`, power-on/cycle, `imex` check/reset, NVSwitch fix/SDN-reset/system-reset, `bmc-recovery`, `mac-change`, and Slurm `drain`/`undrain`/`scancel` for node quarantine.

**Coordination & knowledge**
- Advisory **multi-operator rack locks** (`fcntl.flock`, `var/cache/rack_locks.json`) — implicit active-op tracking + explicit 30-min claims — so a mixed Dell/NVIS/MS crew does not clobber each other's racks.
- **Workflow / MOP engine**: visual Mermaid + React Flow runbooks with a state-machine executor (pending/running/waiting/completed/failed) and AI-generated workflows.
- **AI assistant** (NVIDIA NIM / OpenAI-compatible, streaming SSE) that is context-aware of the current rack/view.
- **Interactive web terminals** (xterm.js over WebSocket) to head and compute nodes.

**Auth & secrets**
- Token or PAM login; encrypted secrets vault (`var/secrets/`, Fernet + PBKDF2); optional outbound NVFTP SFTP cache mirroring.

---

## 3. Architecture & Tech Stack

| Layer | Detail |
|---|---|
| **Backend** | Python 3.10+ / Flask 3, single `backend/app.py` (~12,957 lines), ~120 `@app.route` endpoints, threaded WSGI (`app.run(threaded=True)`) + custom WebSocket terminal middleware (`simple_websocket`). |
| **Frontend** | React 19 + TypeScript + Vite SPA, NVIDIA Kaizen UI (`@nvidia/foundations-react-core`) + MUI, Chart.js, React Flow + dagre, xterm.js, mermaid. Built to `static/spa`, served by Flask. |
| **Packaging** | Multi-stage Docker: `node:22-slim` builds the SPA → `ubuntu:22.04` runtime with `python3` + `openssh-client`. `EXPOSE 5000`, `ENTRYPOINT python3 backend/app.py`. |
| **Persistence** | No DB. JSON/YAML under `var/` on a named volume `rack-data` → `/app/var` (caches, secrets, workflows, logs). Atomic writes via tmp + `os.replace`. |

**Key modules**
- `native_status.py` — Python rack-status table builder with background daemon threads (`ds`, `sinfo`, per-log `--probe-json` probes) + disk caches under `var/cache/`.
- `host_exec.py` — platform-agnostic local/SSH executor.
- `platforms/{bcm,maas}.py` — `PlatformProvider` abstraction (BCM `cmsh`/`pdsh` vs MAAS `maas-cli`).
- `ai_chat.py`, `workflow_engine.py`, `rack_locks.py`, `token_vault.py`, `nvftp_cache_sync.py`, `rack_web/` (PAM), `nvis_id_templates.py`, `demo_data.py`.
- `bin/scripts/` — bundled ops shell scripts executed via SSH/pdsh (`rack_status.sh`, `gpu_reset.sh`, `nvswitch_*`, `imex_*`, `bmc-recovery.sh`, `sysinfo.sh`, `run_nvloom/clusterkit/nemo/llama`, etc.).

**Execution modes**
- `RACK_EXEC_MODE=local` — the app runs directly on the head node.
- `RACK_EXEC_MODE=ssh` — the container SSHes to the head node via OpenSSH subprocess (compute nodes reached with `ssh -J` jump).

---

## 4. Data Sources

- **BCM via `cmsh`** (SSH or local): `rack;list` (inventory), `ds` (per-node up/down/installing), `device … use rf0; get ip` (hostname → **rf0 BMC IP map**, the *only* BMC info surfaced — never queried by a protocol), `device power on/off`.
- **MAAS via `maas-cli`** (BCM alternative): `machines read`, `tags read`, `machine power-on/off`.
- **Slurm CLI** on the head node (behind `module load slurm`): `sinfo -N`, `squeue`, `sacct`, `scontrol show hostnames`.
- **`pdsh`** — parallel fan-out to compute nodes (service restarts, hw checks, bug-report collection, resets).
- **Filesystem log parsing** — NEMO/NCCL `*.txt` logs under `RACK_REMOTE_BASE_PATH/var/logs`, parsed by `rack_status.sh --probe-json` + native Python (validation state, NCCL busbw, LLM step status).
- **LLM endpoint** (outbound HTTPS) — OpenAI-compatible `/chat/completions`, default NVIDIA NIM `integrate.api.nvidia.com`.
- **Grafana** (optional embed, iframe) — `RACK_WEB_GRAFANA_URI` `/d-solo/` panels; PromQL is built server-side but rendered by Grafana, not queried by the backend.
- **NVFTP SFTP** (optional, outbound) — `transfer.nvftp.nvidia.com:22` via paramiko.

> **No direct BMC/Redfish, SNMP, IPMI, or DB polling.** BMC IPs come only from the `cmsh` rf0 mapping.

---

## 5. How It Aids NscaleTX Validation & Handover

This tool is **the thing that produces the Dell/Microsoft acceptance evidence and the day-2 operator console.** The rest of the stack observes; this one *acts*.

**What it uniquely fills (gaps in the current stack):**
1. **Actuation** — the entire 29-container stack is passive/observe-only. `nvis-rack-status` is the only component that can **drive** the test plan (launch NEMO/NCCL/NVLoom/ClusterKit/MNUberGEMM/DCGM-diag/hw-check via Slurm) and **remediate** (gpu-reset, power-cycle, imex/nvswitch reset, bmc-recovery, drain/undrain quarantine).
2. **Operator workflow** — advisory multi-operator rack locks, a codified MOP/runbook workflow engine, log-bundle export for acceptance evidence, and an in-context AI assistant. Nothing else in the stack offers these.
3. **One pane** — it *embeds* the very Grafana (`:3001`) being handed over rather than re-collecting telemetry.

**How it maps to the acceptance program:**
- `bin/scripts` map almost 1:1 onto **NScale_Test_Plan_Dell** categories: Health Check → `checker.sh`/`sysinfo` (CH-01..CH-13), GPU Benchmark & Network Stress → NCCL/NVLoom/ClusterKit (NET-08 all-reduce vs the ≥459 Gbps threshold, CH-07/CH-07.5 PCI/NIC bandwidth), System Stress → MNUberGEMM, NVLink → `nvswitches_rack_audit.sh`, LLMB → NEMO/Nemotron.
- Its **Excel/CSV/zip + bug-report bundles** are the raw per-test PASS/FAIL artifacts that feed `result_schema.json` with Microsoft-acceptance traceability (`msft_acceptance`, Dell-vs-NVIS owner tags mirroring the RACI).
- The **workflow engine** turns tribal bring-up knowledge into versioned, re-runnable MOPs, and the UI + AI assistant lower the day-2 skill floor (field techs can see readiness and reset/power/drain without deep cmsh/Slurm skill).

**Honest overlaps vs the existing stack (two lenses on the same effort, not duplication):**
- **NCCL/LLMB reporting** — the stack already has `nccl-validation`, `llmb-validation`, `cvt-clusterminder` Grafana dashboards (fed by NCP job exporters). Difference in *lens*: rack-status reads **raw Slurm/NCCL logs live per rack** (works even before any exporter exists and is operator-facing for launch+triage); the dashboards are the fleet-wide time-series view once jobs run.
- **GPU thermal/power/DCGM** — the stack's `gpu-health`/`node-deep-dive` dashboards + DCGM exporter own live GPU telemetry. rack-status does **not** re-collect this; it embeds Grafana solo panels. Complementary.
- **Inventory/reachability** — `nvis-invapp-exporter` + `bcm` exporter already give inventory/reachability. rack-status `sysinfo` captures per-node firmware/FRU as an **acceptance snapshot** — different purpose/granularity.

**Not covered by rack-status (the stack keeps these):** facility BMS/CDU coolant telemetry, UFM Validations (e.g. UFM-06 HA failover), Ethernet/Cumulus + IB fabric BER/optical telemetry, and the Parquet data lake. rack-status touches BMC only for NVSwitch Redfish audit + bmc-recovery, not for thermal/PSU/SEL telemetry.

**Metrics-pillar caveat (important):** confirmed **JSON-only, no `/metrics`** endpoint. Its per-rack validation verdicts do **not** reach VictoriaMetrics today and remain a **parallel source of truth**. The clean bridge — not yet built — is a tiny sidecar exporter (invapp-style) that scrapes `/api/status` + `/api/multirack-status` and emits e.g. `nvis_rack_validation_state{rack,su,state}` gauges into VictoriaMetrics `:8429`, which would light up the existing nccl/llmb/cvt dashboards with true per-rack pass/fail.

---

## 6. Deployment Plan

### 6.1 Method (as deployed here)
`docker compose up -d --build` from `/opt/observability/nvis-rack-status-main`, using:
- committed `docker-compose.yml` (unchanged), plus
- a non-destructive **`docker-compose.override.yml`** (auto-merged) that injects the demo/local runtime flags and sets the container name + restart policy, plus
- a **`.env`** (copied/adapted from `.env.example`) supplying the compose **interpolation** values (host port, SSH-key path, host, token).

Compose was chosen over `build-docker.sh dev` because its `restart: unless-stopped` gives **reboot-survival** (the `build-docker.sh dev` path does not set a restart policy), and its default host port avoids the occupied `5050` trap.

### 6.2 Port map

| Scope | Port | Notes |
|---|---|---|
| **Host published** | **`5055/tcp`** | The **only** port that reaches the host. Free on the ObsVM; deliberately avoids the occupied `5050` dev-default. |
| Container-internal | `5000/tcp` | Fixed by `EXPOSE 5000` + `PORT=5000`; namespaced, never conflicts. |
| Outbound 22 | — | SSH to head node + SFTP to NVFTP (only in ssh/NVFTP modes; not used in this demo start). |
| Outbound 443 | — | HTTPS to the LLM endpoint (only if AI key set). |
| Embed 3000→**3001** | — | Grafana iframe; repoint to the ObsVM's existing Grafana at `:3001` when configured. |

**Confirmed-free at deploy time** (via live probe): 5000, 5055, 5080, 8095. **Occupied on the ObsVM** (do not use): 3000 infra-engine, 3001 grafana, 3100 loki, 4317/4318/13133 otel, 5050 (host process), 5433 kea-postgres (127.0.0.1), 8012 invapp, 8090 lldpq-eth, 8428/8429 victoria-metrics, plus the 90xx exporter range and 12346.

### 6.3 Exact steps
1. `cd /opt/observability/nvis-rack-status-main`
2. Confirm Docker + compose and base-image pull works (`ubuntu:22.04`, `node:22-slim`) — **verified reachable**.
3. `.env` present next to the compose file with `RACK_WEB_PORT=5055` and an **absolute** `RACK_SSH_KEY_PATH` (compose mounts the key unconditionally and does **not** expand `~`).
4. `docker-compose.override.yml` present, injecting `RACK_STATUS_DEMO=1`, `RACK_WEB_AUTH_DISABLED=1`, `RACK_EXEC_MODE=local`, `container_name: nvis-rack-status`, `restart: unless-stopped`.
5. `docker compose up -d --build` (first build compiles the SPA + installs pip deps; several minutes).
6. Verify: `docker logs -f nvis-rack-status`; `curl -sf http://localhost:5055/api/status`; open `http://192.168.10.3:5055/spa/`.

### 6.4 Config variables that matter

| Var | Purpose | This deploy |
|---|---|---|
| `RACK_WEB_PORT` | Host published port → container 5000 (the only conflict risk) | **5055** (`.env`) |
| `PORT` | Flask listen port inside container | 5000 (default) |
| `RACK_STATUS_DEMO` | 1 = synthetic data, no cluster access | **1** (override) |
| `RACK_EXEC_MODE` | `local` vs `ssh` | **local** (override) |
| `RACK_WEB_AUTH_DISABLED` | 1 = no login (demo only) | **1** (override) |
| `RACK_SSH_KEY_PATH` | Host path bind-mounted to `/run/secrets/ssh_key` (abs, no `~`) | placeholder file (`.env`) |
| `RACK_PLATFORM` | `bcm` or `maas` | bcm (default) |
| `RACK_SSH_HOST` | Head-node IP (ssh mode) | `127.0.0.1` placeholder (`.env`) |
| `RACK_WEB_AUTH_TOKEN` | Login password (token auth) | empty (`.env`) |
| `RACK_REMOTE_BASE_PATH` | Scripts + log root on head node (ssh mode) | default placeholder (rack-config.env) |
| `NEMO_SQSH_SRC`, `VALIDATION_TEST`, `RACK_VALIDATION_CT_RANGE`, `RACK_SLURM_SKIP_MODULE_LOAD` | Real validation-run config | left at defaults |
| `RACK_WEB_GRAFANA_URI`/`_PORT`, `RACK_AI_API_KEY`, NVIS naming templates | Grafana embed / AI / naming | unset (configure later) |

---

## 7. "Configure Later" Checklist (intentionally unconfigured now)

The tool is running in **demo/local mode** so it starts and serves its UI with **synthetic/empty data**. To connect it to the real GB300 SuperPOD, the operator must later:

- [ ] **Switch to ssh mode.** Delete/empty `docker-compose.override.yml` (or flip its flags): set `RACK_EXEC_MODE=ssh`, `RACK_STATUS_DEMO=0`, and remove `RACK_WEB_AUTH_DISABLED`.
- [ ] **Point at the BCM head node.** `RACK_SSH_HOST=192.168.10.2` (nscale-hn1 / `bcm-hn`) in `.env`; set `RACK_SSH_KEY_PATH` to the real passwordless key (`id_bcm`) and trust its public key on the head node.
- [ ] **Deploy `bin/scripts` to the head node** and set `RACK_REMOTE_BASE_PATH` to where they live; point the log dir at where NEMO/NCCL Slurm output lands (same format as `NscaleTX_docs/Validation Testing/Logs/SU5-WH1H/*`).
- [ ] **Set a real login secret.** `RACK_WEB_AUTH_TOKEN=<strong secret>` in `.env`; rotate off the shipped `changeme`.
- [ ] **NscaleTX naming templates.** Configure `NVIS_RACK_ID`/`NVIS_CT_ID` for the `ink50-dh01-h01-NN` / WH1H convention (Settings UI ships Firmus/CBR/Bright templates).
- [ ] **Grafana embed.** `RACK_WEB_GRAFANA_URI=http://192.168.10.3:3001` + `RACK_WEB_GRAFANA_DASH_UID/SLUG` for a GPU thermal+power dashboard (it is a Grafana *client*, not a competitor — never point it at `:3000`, which is infra-engine).
- [ ] **Validation run config.** `NEMO_SQSH_SRC`, `VALIDATION_TEST` (e.g. `nccl_allreduce,llm`), `RACK_VALIDATION_CT_RANGE` (e.g. `01-18`), `RACK_SLURM_SKIP_MODULE_LOAD=1`.
- [ ] **(Optional) AI assistant.** `RACK_AI_API_KEY=nvapi-…` (+ endpoint/model) to enable the chat widget.
- [ ] **(Optional) NVFTP** offsite cache mirroring (`RACK_NVFTP_SFTP_USER` + token in the vault).

---

## 8. Follow-ups & Risks

**Deployment risks (handled here):**
- **PORT TRAP** — `build-docker.sh dev` / `start.sh` default to host **5050, which is occupied** on the ObsVM. Avoided by publishing **5055** via compose.
- **COMPOSE SSH-KEY MOUNT** — the key volume is mounted **unconditionally** (even in demo) and `~` is **not** expanded. Handled by pointing `RACK_SSH_KEY_PATH` at an absolute placeholder file (`deploy-secrets/placeholder_ssh_key`).
- **INTERPOLATION SOURCE** — compose `${…}` reads shell/`.env`, **not** `rack-config.env`. Host port + key path are therefore set in `.env`.
- **BUILD-FROM-SOURCE** — compose uses `build: .` and no image is cached; the first deploy needs registry access (verified). On a future air-gapped host use `build-docker.sh save` → `docker load`.

**Standing risks / follow-ups:**
- **FABRIC EXPOSURE** — the container binds `0.0.0.0:5000` and the default publish exposes 5055 on **all** interfaces of the dual-homed ObsVM (mgmt **and** `10.40` fabric). To restrict to mgmt only, publish `192.168.10.3:5055:5000` (do this cleanly by overriding the whole `ports` list, not by appending a second entry). *Left as a follow-up so the committed compose `ports` list is not double-bound.*
- **AUTH HYGIENE** — demo runs with auth **disabled**. Set a real token and remove the disable flag before any real use. `rack-config.env` ships `RACK_WEB_AUTH_TOKEN` guidance with `changeme` — rotate it.
- **HARDCODED BMC PASSWORD** — `bin/scripts/nvswitches_rack_audit.sh` ships a hardcoded Dell BMC password `WelcomeDell1!` that **must be parameterized/rotated** per the program's sanitization mandate before NVSwitch audit is used.
- **NO HEALTHCHECK** — compose defines none; the container shows "running" even if it cannot reach the cluster. Monitor via `docker logs` and the `/api/status` probe.
- **NAMED-VOLUME PERSISTENCE** — state (secrets, workflow runs, cache, logs) lives in the `rack-data` volume; `docker compose down -v` or a prune wipes it, and `var/secrets/` may hold sensitive material.
- **PARALLEL SOURCE OF TRUTH** — no `/metrics`; add the invapp-style sidecar exporter to bridge per-rack verdicts into VictoriaMetrics if the metrics pillar should reflect them.
- **RBAC** — auth is a shared token/PAM with advisory-only locks (no per-user RBAC), yet the tool can actuate power/reset/drain. Use the `RACK_*_DISABLED` guardrail flags and rotate credentials before handing keys to a mixed-vendor floor.
