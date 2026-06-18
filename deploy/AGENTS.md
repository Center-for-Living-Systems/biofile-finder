# AGENTS.md

The authoritative guide for this self-hosted deployment — architecture, accounts & roles,
security, credentials, and operations — is **[README.md](./README.md)** in this folder.
Read it fully before making changes.

Quick rules for agents:
- Work on `main` (the box deploys from it); put deploy changes under `deploy/`.
- **Never commit secrets** — `deploy/.env` is gitignored; verify with `git check-ignore deploy/.env`.
- **Don't broaden `/gardel`** beyond the manifest-built allowlist (it would expose unpublished data).
- Use the existing `build-*.py` generators; they encode the manifest contracts.
