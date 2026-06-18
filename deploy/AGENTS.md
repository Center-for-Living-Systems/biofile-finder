# AGENTS.md — Self-Hosted BioFile Finder (Gardel Lab)

Authoritative guide to this deployment for humans **and** AI agents. If you are an
agent picking up work here, read this top-to-bottom first. It describes what the
system is, how it's wired, where everything lives, and how to operate it.

> **No secrets in this file.** Real credentials live only in `deploy/.env` (gitignored)
> and `/etc/*.cred` on the box. Never paste passwords into committed files.

---

## TL;DR

- A **fork of [BioFile Finder](https://github.com/AllenInstitute/biofile-finder)** (Allen
  Institute), pinned to release **v9.0.0**, customized to self-host Gardel Lab microscopy data.
- The app is **100% client-side** (DuckDB-WASM in the browser). No app backend/database.
  A web server (**Caddy**) just serves static files + CSV manifests.
- **Live at https://128.135.108.226/** — **PUBLIC, no login** (auth was removed by operator
  decision). Self-signed HTTPS.
- The repo **is** the deployment: everything is under `deploy/`, the box runs from branch
  **`main`**, and `main` = `v9.0.0 + deploy commits`.
- Datasets appear on **`/datasets`**; each is a CSV "manifest" of files + PNG previews.
  Raw image files stream from a **read-only NAS mount**; only files listed in a manifest
  are web-reachable (allowlist).

---

## 1. Architecture

```
                     Browser  (https, self-signed, NO auth)
                                 │
        ┌──────────────────── Caddy (systemd) ────────────────────┐
        │  site 128.135.108.226   tls internal                    │
        │                                                         │
        │  /robots.txt → Disallow: /                              │
        │  /data/*   → /srv/shared            (master manifest,   │
        │                                      per-dataset         │
        │                                      manifests, PNG      │
        │                                      previews, local     │
        │                                      datasets)           │
        │  /gardel/* → /srv/published/gardel  (ALLOWLIST symlink   │
        │                                      tree → read-only    │
        │                                      NAS; only manifest- │
        │                                      listed files)       │
        │  /*        → /srv/www/biofile-finder (built app, SPA     │
        │                                       fallback to        │
        │                                       index.html)        │
        └─────────────────────────────────────────────────────────┘
```

**How `/datasets` works (the core flow):**
1. Browser loads the static app from `/srv/www/biofile-finder` (client routes like
   `/datasets`, `/app` are served `index.html` via SPA fallback).
2. The app fetches the **master dataset list** from `${DatasetBucketUrl}/Dataset+Manifest.csv`.
   `DatasetBucketUrl` is **baked into the build** = `https://128.135.108.226/data`
   (see `packages/core/constants/index.ts`).
3. Each row of that CSV is one dataset (a `PublicDataset`). Clicking it runs the row's
   **`Specific query`**, which loads that dataset's own **file manifest**.
4. The file manifest lists every file with a **`File Path`** URL (the openable file) and a
   **`Thumbnail`** URL (generated PNG preview). DuckDB-WASM queries it in-browser for the
   filter/sort/grid UI.

**Two manifest types — do not confuse them:**

| Manifest | Path | Purpose | Required headers |
|----------|------|---------|------------------|
| **Master** | `/srv/shared/Dataset+Manifest.csv` | the list on `/datasets` | **display labels**: `Dataset name`, `File Path`, `Featured`, `Specific query`, `Short description`, `File count`, `Size`, `Creation date`, `Organization` |
| **Per-dataset** | `/srv/shared/_derived/**/<id>-manifest.csv` | files within one dataset | `File Path`, `Thumbnail`, `File Name`, `File Size`, + metadata facets (`Condition`, `Kind`, `Replicate`, …) |

> ⚠️ The master manifest headers **must be the display labels** (the app maps columns by
> `annotation.name === displayLabel`). Using machine names (`dataset_name`, `featured`, …)
> yields an **empty `/datasets` page**. This is the #1 gotcha.

**Previews:** CZI (Zeiss) and microscopy TIF do not render in browsers, so each image gets a
512px max-projection **PNG** preview. Previews + manifests are written to **local disk**
(`/srv/shared/_derived/`), never to the NAS (read-only).

---

## 2. Repo layout (everything is here)

```
biofile-finder/                 fork, branch main = v9.0.0 + deploy commits
├── packages/…                  app source (v9.0.0 + the 3 customizations in §6)
└── deploy/
    ├── AGENTS.md               ← this file (authoritative)
    ├── DEPLOYMENT-LOG.md        task history (from the build)
    ├── deployment-history.jsonl raw task export
    ├── .env                     CREDENTIALS (gitignored, mode 600)
    ├── .env.example             committed template
    ├── .venv/                   Python venv for CZI/TIF thumbnailing (gitignored)
    ├── mount-nas.sh             mount the NAS read-only using .env
    ├── build-nas-dataset.py     previews + per-dataset manifest for a NAS folder
    ├── build-shared-dataset.py  same, for a local /srv/shared folder
    ├── build-master-manifest.py (re)generate the /datasets master list
    ├── publish-symlinks.py      build the /gardel allowlist from the manifests
    ├── serve-app-static.sh      deploy build to /srv/www + Caddy static/SPA serving
    ├── add-data-route.sh        add the /data Caddy route (historical)
    ├── setup-caddy-auth.sh      Caddy + Basic Auth + ufw (historical; auth now OFF)
    └── provision.sh, demo-*     early bootstrap + synthetic demo (superseded)
```

---

## 3. Where things live on the box

| Path | What | Served at |
|------|------|-----------|
| `/srv/www/biofile-finder/` | built app (static) | `/` |
| `/srv/shared/` | manifests, previews, local datasets | `/data/*` |
| `/srv/shared/Dataset+Manifest.csv` | master dataset list | `/data/Dataset+Manifest.csv` |
| `/srv/shared/_derived/` | previews + per-dataset manifests | `/data/_derived/*` |
| `/srv/gardelnas/` | **NAS** mount (`//psd-gardelnas.uchicago.edu/Expansion`, read-only) | — (not served directly) |
| `/srv/published/gardel/` | symlink **allowlist** → only manifest-listed NAS files | `/gardel/*` |
| `/etc/caddy/Caddyfile` | web server config | — |
| `/etc/gardelnas.cred` | NAS SMB creds (600, root; generated from `.env`) | — |
| `/home/dsadmin/biofile-finder/` | the repo / source checkout | — |

**Services:** only **`caddy`** (systemd; auto-start, auto-restart). `systemctl status caddy`,
logs `journalctl -u caddy -f`. (The old `biofile-finder-demo` Python server was removed.)

---

## 4. Security model — READ THIS

- **PUBLIC, no authentication.** The box is on a **public IP** (`128.135.108.226`), so anyone
  on the internet can reach the app and the served data. This was an explicit operator choice.
- **`/gardel` is an allowlist**, not the whole NAS. It serves `/srv/published/gardel`, a tree
  of symlinks containing **only files referenced by the dataset manifests**. The other ~26 lab
  members' folders on the NAS are **not** web-reachable. **Do not** repoint `/gardel` at
  `/srv/gardelnas` (the whole share) — that would expose everyone's unpublished data.
- **NAS is read-only** (`ro` mount + read-only service account). No writes are possible.
- **TLS** is self-signed (Caddy `tls internal`) — no public DNS name exists for this box, so
  Let's Encrypt can't issue. Browsers warn unless the Caddy root CA is trusted on the client
  (`/var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt`).
- **Firewall:** `ufw` allows inbound 22/80/443 only.
- **`robots.txt`** disallows all crawlers (courtesy; not enforcement).

To **re-enable a login** later: set `AUTH_USER`/`AUTH_PASS` in `.env`, add a `basic_auth` block
to the Caddyfile (`caddy hash-password`), `systemctl reload caddy`. See `setup-caddy-auth.sh`.

---

## 5. Credentials (`deploy/.env`)

All secrets live in **`deploy/.env`** (gitignored, `chmod 600`). Template: `.env.example`.

| Key | Meaning |
|-----|---------|
| `NAS_HOST` / `NAS_SHARE` | `psd-gardelnas.uchicago.edu` / `Expansion` |
| `NAS_USER` / `NAS_PASS` | `image_service` / (secret) |
| `NAS_DOMAIN` | **blank** — specifying `adlocal` causes `LOGON_FAILURE` |
| `NAS_MOUNT` | `/srv/gardelnas` |
| `PUBLIC_HOST` | `128.135.108.226` |
| `AUTH_USER` / `AUTH_PASS` | optional; only if re-enabling Basic Auth |

`mount-nas.sh` reads `.env` to write `/etc/gardelnas.cred` and mount. If you re-clone the repo
elsewhere, `cp .env.example .env` and fill it in (`.env` exists only on the box).

---

## 6. Source customizations vs. upstream v9.0.0

Three commits on top of v9.0.0 (require a rebuild if changed):

1. `packages/core/constants/index.ts` — `DatasetBucketUrl` (all envs) → `https://128.135.108.226/data`
   so `/datasets` reads our master manifest instead of Allen's S3.
2. `packages/web/webpack/index.html` — removed Google Tag Manager (Allen analytics).
3. `packages/web/src/components/Footer/index.tsx` — removed the dead OneTrust "Cookie settings"
   button (its SDK isn't loaded here).

Upstream contracts we rely on (stable as of v9.0.0): openable column `File Path` (or top-level
`file_path`); thumbnail column `Thumbnail`; `${DatasetBucketUrl}/Dataset+Manifest.csv`; the
display-label column mapping for the master manifest.

---

## 7. Common operations

All `build-*.py` run via the venv: `deploy/.venv/bin/python …`. Most steps need **no sudo**
(dsadmin is in the `researchers` group; `/srv/shared` and `/srv/published` are group-writable).

### Add a NAS dataset to `/datasets`
```bash
cd /home/dsadmin/biofile-finder/deploy
# 1. previews + per-dataset manifest (reads files over SMB)
.venv/bin/python build-nas-dataset.py --src "/srv/gardelnas/<path to dataset folder>" \
    --id "<short-slug>" --name "<label shown in the file view>"
# 2. rebuild the /gardel allowlist so the new files are reachable
.venv/bin/python publish-symlinks.py
# 3. add an entry to DATASETS in build-master-manifest.py, then regenerate the list
python3 build-master-manifest.py
```
Hard-refresh `/datasets`. No rebuild, no sudo.

### Add a LOCAL dataset (files copied into `/srv/shared`)
Use `build-shared-dataset.py` (served from `/data` instead of `/gardel`), then add a row in
`build-master-manifest.py` and re-run it. (No `publish-symlinks.py` needed.)

### Refresh a dataset (files changed)
Re-run the same `build-*-dataset.py` + (for NAS) `publish-symlinks.py`.

### Mount / remount the NAS
```bash
sudo bash deploy/mount-nas.sh        # uses .env; idempotent
# after a reboot it auto-mounts; if the NAS was down: sudo mount /srv/gardelnas
```

### Rebuild the app (only for code/config changes)
```bash
cd /home/dsadmin/biofile-finder
npm ci && npm --prefix packages/web run build
sudo rsync -a --delete packages/web/dist/ /srv/www/biofile-finder/
sudo chmod -R a+rX /srv/www/biofile-finder
sudo systemctl reload caddy
```

### Update to a newer upstream release
```bash
cd /home/dsadmin/biofile-finder
git fetch upstream
git rebase upstream/main          # or rebase onto a specific tag, e.g. v9.1.0
# resolve any conflicts in the 3 customized files (§6), then rebuild + redeploy as above.
git push --force-with-lease origin main
```
Before redeploying a big jump, verify the datasets machinery is unchanged
(`PublicDataset`, `useDatasetDetails`, `${DatasetBucketUrl}/Dataset+Manifest.csv`,
`File Path`/`Thumbnail`). Snapshot `/srv/www` first for instant rollback.

### Trust the cert (kills the browser warning, per client machine)
```bash
sudo install -m644 /var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt /tmp/caddy-root-ca.crt
# copy to client and trust it (macOS Keychain 'Always Trust' / Ubuntu update-ca-certificates / Windows certutil -addstore Root)
```

---

## 8. Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `/datasets` empty | Master manifest headers must be **display labels** (`Dataset name`, `File Path`, `Featured`, `Specific query`…). Regenerate `build-master-manifest.py`. Hard-refresh. |
| Dataset opens, no files | Per-dataset manifest needs a `File Path` column with reachable URLs. `curl -k <File Path URL>` should be 200. |
| Published file 404 | Not in the `/gardel` allowlist — re-run `publish-symlinks.py` after onboarding. |
| No thumbnails | `Thumbnail` URL must resolve under `/data/_derived/…`. Re-run the dataset builder. |
| `/datasets` 404 (route) | App not served with SPA fallback — re-run `serve-app-static.sh`. |
| Browser cert warning | Expected (self-signed). Trust the root CA (§7) or click through. |
| NAS files 403/404 | `mountpoint /srv/gardelnas`? `sudo mount /srv/gardelnas`. Caddy must be in `researchers` group. |
| Empty page after rebuild | Hard-refresh (Ctrl/Cmd-Shift-R) to drop the cached old JS bundle. |

---

## 9. Conventions for agents working here

- **The repo is the deployment.** Work on `main`; the box deploys from `main`. Commit deploy
  changes under `deploy/`.
- **Never commit secrets.** `deploy/.env` and `*.crt` are gitignored — keep it that way.
  Verify with `git check-ignore deploy/.env` before committing.
- **Don't broaden `/gardel`** beyond the manifest allowlist (it would expose other labs' data).
- **Sudo** on this box requires a password (the operator's). Scripts that need root say so;
  hand them to the operator or run with explicit sudo — don't hardcode the password anywhere.
- Prefer the existing generators over ad-hoc edits; they encode the manifest contracts above.
