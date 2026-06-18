# Self-Hosted BioFile Finder — Deployment Guide (Gardel Lab)

The single source of truth for this deployment, for humans **and** AI agents. Agents: read
this fully before changing anything.

> **No secrets in this file.** Credentials live only in `deploy/.env` (gitignored) and
> `/etc/*.cred` on the box. Never commit passwords.

## What it is

- A fork of [BioFile Finder](https://github.com/AllenInstitute/biofile-finder) (Allen Institute),
  pinned to **v9.0.0**, self-hosting Gardel Lab microscopy data.
- **100% client-side** app (DuckDB-WASM in the browser); no backend. **Caddy** serves static
  files + CSV manifests.
- **Live: http://128.135.108.226/** — **public, no login, plain HTTP** (no TLS; acceptable
  because the data is public and there's no login).
- The repo **is** the deployment: everything is under `deploy/`; the box runs from branch
  **`main`** (= v9.0.0 + our commits).
- Datasets appear on **`/datasets`**. Raw images stream from a **read-only NAS**, but only files
  listed in a published manifest are web-reachable (an allowlist).

## Accounts & roles (this machine)

| Account | Role |
|---------|------|
| `lding` (1000) | Box owner / primary desktop user; in `sudo`. |
| `dsadmin` (1001) | **Operator account** — in `sudo`; owns the repo and `/srv/www`; runs builds, generators, and deploys. Day-to-day work happens here. |
| `caddy` (997) | Runs the Caddy web server (systemd); the **only** account serving traffic. Added to `researchers` so it can read served files. |
| `bff` (1002) | Service account from early setup; **now unused** — the static app needs no runtime account. Harmless to leave. |
| `image_service` | **Remote** AD/SMB account (`adlocal` domain) for the NAS — *not* a local Linux user. Read-only. Stored in `deploy/.env` → `/etc/gardelnas.cred`. |
| group `researchers` (1003) | Read access to the served data. Members: `lding, dsadmin, bff, caddy`. The NAS mounts with this group so Caddy can read it. |
| `root` | Owns `/etc/caddy/Caddyfile`, `/etc/gardelnas.cred`, and `/srv/shared`. Caddy/mount/firewall changes need sudo. |

Sudo requires the operator's password (not stored anywhere in the repo).

## Architecture

```
   Browser (plain HTTP, no auth)
        │
   Caddy (systemd, runs as `caddy`)  —  site http://128.135.108.226 (no TLS)
        ├─ /data/*   → /srv/shared            manifests, PNG previews, local datasets
        ├─ /gardel/* → /srv/published/gardel  allowlist symlinks → read-only NAS
        ├─ /robots.txt → Disallow: /
        └─ /*        → /srv/www/biofile-finder built app (SPA fallback to index.html)
```

**`/datasets` flow:** the app loads statically → fetches the **master** `Dataset+Manifest.csv`
from the baked URL `http://128.135.108.226/data` (`packages/core/constants/index.ts`) → each row
is a dataset whose **`Specific query`** loads that dataset's **file manifest** → files are shown
with a **`File Path`** (openable) and a **`Thumbnail`** (PNG preview).

**Two manifest types:**
- **Master** — `/srv/shared/Dataset+Manifest.csv`, the `/datasets` list. Headers **must be the
  display labels** (`Dataset name`, `File Path`, `Featured`, `Specific query`, `Short description`,
  `File count`, `Size`, …). Machine names → an **empty `/datasets` page** (the #1 gotcha).
- **Per-dataset** — `…/_derived/<id>-manifest.csv`, the files in one dataset: `File Path`,
  `Thumbnail`, `File Name`, `File Size`, + facets (`Condition`, `Kind`, `Replicate`, …).

CZI/TIF don't render in browsers, so we generate 512px PNG previews on **local** disk
(`/srv/shared/_derived/`) — never on the read-only NAS.

## Paths

| Path | What | Owner | Served at |
|------|------|-------|-----------|
| `/srv/www/biofile-finder/` | built app (static) | dsadmin | `/` |
| `/srv/shared/` | manifests, previews, local datasets | root:researchers | `/data/*` |
| `/srv/shared/Dataset+Manifest.csv` | master dataset list | — | `/data/Dataset+Manifest.csv` |
| `/srv/published/gardel/` | allowlist symlinks → manifest-listed NAS files | dsadmin:researchers | `/gardel/*` |
| `/srv/gardelnas/` | NAS mount (`//psd-gardelnas.uchicago.edu/Expansion`, read-only) | dsadmin:researchers | — |
| `/etc/caddy/Caddyfile` · `/etc/gardelnas.cred` | web + NAS config | root | — |
| `/home/dsadmin/biofile-finder/` | the repo / source | dsadmin | — |

Only service: **`caddy`** (systemd; auto-start/restart). Logs: `journalctl -u caddy -f`.

## Security

- **Public, no auth, plain HTTP** — unencrypted in transit, which is fine *only* because the
  data is public and there's no login. **If you ever add a login, restore TLS first** — Basic
  Auth over HTTP sends the password in cleartext.
- **`/gardel` is an allowlist** (`/srv/published/gardel`, built by `publish-symlinks.py` from the
  manifests). It exposes only published files. **Never** repoint it at `/srv/gardelnas` — that
  would publish every lab member's unpublished data.
- NAS is **read-only**. `ufw` allows inbound **22/80** only. `robots.txt` disallows crawlers.

## Credentials — `deploy/.env`

Gitignored, `chmod 600`. Template: `.env.example`. Keys: `NAS_HOST`, `NAS_SHARE`, `NAS_USER`,
`NAS_PASS`, `NAS_DOMAIN` (blank — `adlocal` causes `LOGON_FAILURE`), `NAS_MOUNT`, `PUBLIC_HOST`,
and optional `AUTH_USER`/`AUTH_PASS`. `mount-nas.sh` reads it to write `/etc/gardelnas.cred` and
mount. Re-cloning elsewhere: `cp .env.example .env` and fill in (`.env` lives only on the box).

## Source changes vs upstream v9.0.0 (rebuild if changed)

1. `packages/core/constants/index.ts` — `DatasetBucketUrl` → `http://128.135.108.226/data`.
2. `packages/web/webpack/index.html` — removed Google Tag Manager.
3. `packages/web/src/components/Footer/index.tsx` — removed the dead OneTrust button.

## Operations

`build-*.py` run via the venv (`deploy/.venv/bin/python`). No sudo unless noted (dsadmin is in
`researchers`; `/srv/shared` and `/srv/published` are group-writable).

```bash
cd /home/dsadmin/biofile-finder/deploy

# Add a NAS dataset to /datasets:
.venv/bin/python build-nas-dataset.py --src "/srv/gardelnas/<dataset folder>" --id "<slug>" --name "<label>"
.venv/bin/python publish-symlinks.py          # refresh the /gardel allowlist
# then add an entry to DATASETS in build-master-manifest.py and:
python3 build-master-manifest.py              # regenerate the /datasets list
# hard-refresh /datasets — no rebuild, no sudo

# Add a LOCAL dataset (files under /srv/shared): build-shared-dataset.py, then build-master-manifest.py
# Refresh a dataset (files changed): re-run the same build-*-dataset.py (+ publish-symlinks.py for NAS)

# Mount / remount the NAS (uses .env):
sudo bash mount-nas.sh                          # after reboot it auto-mounts; if down: sudo mount /srv/gardelnas

# Rebuild the app (only for code/config changes):
cd /home/dsadmin/biofile-finder && npm ci && npm --prefix packages/web run build
sudo rsync -a --delete packages/web/dist/ /srv/www/biofile-finder/ && sudo chmod -R a+rX /srv/www/biofile-finder
sudo systemctl reload caddy

# Update to a newer upstream release:
git fetch upstream && git rebase upstream/main   # resolve conflicts in the 3 files above, then rebuild + redeploy
git push --force-with-lease origin main
```

**Switch HTTP ↔ HTTPS:** the scheme is baked into the build and the manifest URLs. Edit
`DatasetBucketUrl`, set the matching `HOST` scheme in the `build-*.py` generators, regenerate
manifests (or `sed -i 's#http://#https://#g'` the CSVs under `/srv/shared`), rebuild + redeploy,
and set the Caddy site to `http://…` or `https://… { tls internal }`. Currently HTTP-only.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `/datasets` empty | Master manifest headers must be **display labels**. Re-run `build-master-manifest.py`, hard-refresh. |
| Dataset opens, no files | Per-dataset manifest needs a `File Path` column with reachable URLs (`curl <url>` = 200). |
| Published file 404 | Re-run `publish-symlinks.py` (file isn't in the allowlist). |
| No thumbnails | `Thumbnail` URL must resolve under `/data/_derived/…`. Re-run the dataset builder. |
| `/datasets` route 404 | App not served with SPA fallback — re-run `serve-app-static.sh`. |
| Won't load over `https://` | Expected — HTTP-only. Use `http://128.135.108.226/`. |
| Empty page after rebuild | Hard-refresh (Ctrl/Cmd-Shift-R) to drop the cached old bundle. |
| NAS files 404/403 | `mountpoint /srv/gardelnas`? `sudo mount /srv/gardelnas`. Caddy must be in `researchers`. |

## For agents / contributors

- Work on `main` (the box deploys from it); commit deploy changes under `deploy/`.
- **Never commit secrets** — verify `git check-ignore deploy/.env` before committing.
- **Don't broaden `/gardel`** beyond the manifest allowlist.
- Prefer the existing generators (they encode the manifest contracts above).
- Build/task history: `DEPLOYMENT-LOG.md`.
