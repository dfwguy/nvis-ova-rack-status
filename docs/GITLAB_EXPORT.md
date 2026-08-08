# GitLab handoff

This repository was prepared on the NscaleTX observability VM on
2026-08-08. It is deliberately a new, credential-free history rather than an
export of the deployment repository's existing history.

The first commit and tag `downloaded-original-sanitized-20260605` preserve the
downloaded `/opt/observability/nvis-rack-status-main` baseline. The second
commit contains the current enhanced source from
`/opt/observability/nvis-rack-status-v3`, including the uncommitted 15-minute
BCM rack-inventory cache and its unit test. Git therefore provides an exact
line-level audit:

```bash
git diff downloaded-original-sanitized-20260605..main
git diff --stat downloaded-original-sanitized-20260605..main
git log --stat --oneline downloaded-original-sanitized-20260605..main
```

The word `sanitized` matters. Instance `.env` files, deployment overrides,
SSH keys, token vaults, runtime databases, logs, caches, backup files, and
generated SPA bind mounts are excluded. Hard-coded switch/BMC/Grafana
password defaults present in the downloaded source were replaced in both
commits by required environment variables, so they do not exist anywhere in
the exported Git history. The exact private deployment remains in the local
rollback snapshot documented separately.

## Push to an internal GitLab project

After copying the bundle to a machine that can reach GitLab:

```bash
git clone nvis-rack-status-gitlab-20260808.bundle nvis-rack-status
cd nvis-rack-status
git remote add origin git@gitlab.example.internal:GROUP/PROJECT.git
git push -u origin main
git push origin --tags
```

Replace only the GitLab URL. Verify the accompanying SHA-256 file before
cloning. Do not add the ObsVM deployment override or secret files to Git.

## Recreate deployment configuration

Use `docker-compose.override.example.yml` and a local, ignored `.env`. The
production deployment has site-specific bind mounts and credentials that are
captured only in the private rollback snapshot. CI should build from source;
the live image archive is a rollback artifact, not a source-control artifact.

