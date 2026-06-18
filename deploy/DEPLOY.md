# BioFile Finder — Self-Hosted Deployment (status + next steps)

Live deployment status for the fork of `Center-for-Living-Systems/biofile-finder`
on this Ubuntu box. Companion to the original runbook `~/bio_finder.md`.
Work items are tracked in **beads** (`bd`, prefix `bff-`) in this directory.

_Last surveyed: 2026-06-15._

---

## Box facts (verified on the box)

| Thing | State |
|-------|-------|
| Admin user | `dsadmin` (uid 1001, in `sudo` group — **but sudo prompts for a password**) |
| Service account | `bff` (uid 1002) exists ✓ |
| Node | `v20.20.2` / npm `10.8.2`, system-wide at `/usr/bin/node` ✓ |
| Repo | cloned at `/home/dsadmin/biofile-finder`, clean `main` @ `97697a2d` ✓ |
| Deps + build | `npm ci` done, `packages/web/dist/index.html` present (build succeeds) ✓ |
| Hostname / IP | `lding-Dell-Pro-Max-Tower-T2-FCT2250` / `128.135.108.226` (no public DNS) |
| Caddy / cifs-utils / `/srv/nas` | none installed, share not mounted ✗ |
| Ports 80/443/8080 | nothing listening |

## Decisions made

- **Access model:** Caddy **internal TLS (self-signed)** — no public domain, so
  Let's Encrypt is out. Clients must trust Caddy's local CA (or click through).
- **Repo home:** **move the checkout to `/home/bff/biofile-finder`**, owned by `bff`.
  `bff` owns updates, builds, the NAS-mount uid/gid, and the manifest script.

## Open questions — all resolved

1. **Build output dir** = `packages/web/dist` (confirmed: `index.html` present).
2. **Dataset column contract:** the openable path is `FileDetail.path`
   (`packages/core/entity/FileDetail/index.ts`), which reads top-level `file_path`
   **or** an annotation literally named **`File Path`**. A value starting with
   `http`/`s3` is treated as remote and opened in-browser. → manifest puts full
   `https://<host>/nas/...` URLs in a **`File Path`** column; other columns become
   searchable metadata.
3. **No backend:** `DataSourceService.getAll()` is a `[]` placeholder, queries run
   in DuckDB-WASM client-side, no `file-explorer-service` refs in `packages/web/src`.
   Client-side only — nothing else to run.
4. **`.env`:** none needed. Build-time vars are only `AMPLITUDE_API_KEY` (optional
   analytics), `APPLICATION_VERSION`, `NODE_ENV`, `WEBPACK_DEV_SERVER_PORT`.

---

## Local demo (no NAS, no sudo) — works now

While the NAS details are outstanding, the whole serving + manifest pipeline runs
locally with a synthetic dataset:

```bash
bash ~/biofile-finder/deploy/demo-local.sh        # serves on http://localhost:8080
```
- `demo-data-gen.py` writes 24 fake microscopy PNGs under `demo-data/`
  (Plate/Well/Condition/Channel/Timepoint) plus `manifest.csv` whose **File Path**
  column holds `http://localhost:8080/nas/...` URLs.
- `demo-local.sh` symlinks the built app + the data into one web root and serves
  both, then prints the manifest URL to load via the app's **+ Add Data Source**.
- Verified: app `200`, manifest `200`, PNGs serve as `image/png 200`.

When the NAS arrives, the same manifest shape applies — only the file root and the
`BASE_URL` change (steps C/E below).

## Next steps (tracked as beads — see `bd ready`)

### A. Re-home the repo to `bff`  _(sudo; run via `! ...`)_
```bash
sudo rsync -a --chown=bff:bff /home/dsadmin/biofile-finder/ /home/bff/biofile-finder/
sudo -u bff -i bash -c 'cd ~/biofile-finder && git status && ls packages/web/dist/index.html'
# once verified: sudo rm -rf /home/dsadmin/biofile-finder
```

### B. Smoke-test the existing build  _(no sudo, reversible)_
```bash
cd /home/bff/biofile-finder/packages/web/dist && python3 -m http.server 8080
# browse http://localhost:8080 (or ssh -L 8080:localhost:8080) — confirm UI renders
```

### C. Mount the NAS read-only  _(sudo; BLOCKED on NAS details)_
Needs: NAS host, share name, SMB username/password/domain.
```bash
sudo apt install -y cifs-utils
sudo install -m600 /dev/null /etc/biofile-finder-smb.cred   # username=/password=/domain=
sudo mkdir -p /srv/nas
# /etc/fstab:
# //<nas-host>/<share> /srv/nas cifs credentials=/etc/biofile-finder-smb.cred,uid=bff,gid=bff,ro,vers=3.0,_netdev,nofail 0 0
sudo mount -a && ls /srv/nas
```

### D. Install Caddy + self-signed TLS  _(sudo)_
`/etc/caddy/Caddyfile`:
```
lding-Dell-Pro-Max-Tower-T2-FCT2250, 128.135.108.226 {
    tls internal
    handle_path /nas/* { root * /srv/nas
        file_server }
    handle {
        root * /home/bff/biofile-finder/packages/web/dist
        file_server
        try_files {path} /index.html
    }
}
```
Then `sudo systemctl enable --now caddy`. Firewall: allow 80/443 + SSH only.

### E. Generate the manifest  _(as bff; BLOCKED on C)_
Runbook step 8 script, but `BASE_URL = "https://lding-Dell-Pro-Max-Tower-T2-FCT2250/nas"`.

### F. Hardening / ops
`unattended-upgrades`, `PasswordAuthentication no` in sshd, distribute Caddy's
internal root CA to client machines so HTTPS is trusted.

---

## Dependency order

```
A (re-home) ──┬─> B (smoke-test)
              └─> D (Caddy) ──> E (manifest) ──┐
C (NAS mount) ───────────────────────────────> E
                              D, A ───────────> F (hardening)
```
