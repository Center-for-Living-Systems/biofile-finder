# AGENTS.md

This repo is a **self-hosted fork of BioFile Finder** (Allen Institute), deployed on a Gardel
Lab box. The app source is upstream's; all deployment code, configuration, accounts/roles, and
operations live under **`deploy/`**.

**Read [`deploy/README.md`](./deploy/README.md) first** — it's the authoritative guide
(architecture, accounts & roles, security model, credentials, operations, troubleshooting).

## Quick orientation

- **Live:** http://128.135.108.226/ — public, no login, plain HTTP.
- **Branch:** the box deploys from `main` (= upstream v9.0.0 + our deploy commits).
- **The app is client-side** (DuckDB-WASM); no backend. Caddy serves static files + CSV manifests.
- **Operator account:** `dsadmin` (sudo). Web server runs as `caddy`. See the Accounts & roles
  table in `deploy/README.md`.

## Rules for agents

- Work on `main`; put deployment changes under `deploy/`.
- **Never commit secrets.** Credentials live only in `deploy/.env` (gitignored) and `/etc/*.cred`
  on the box. Verify with `git check-ignore deploy/.env` before committing.
- **Don't broaden `/gardel`** beyond the manifest-built allowlist (`deploy/publish-symlinks.py`) —
  it would expose lab members' unpublished NAS data.
- Use the existing `deploy/build-*.py` generators; they encode the manifest column contracts.
- After app/source changes, rebuild + redeploy per `deploy/README.md` (§ Operations).
