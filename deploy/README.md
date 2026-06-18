# Self-Hosted BioFile Finder — Operations README

A self-hosted deployment of [BioFile Finder](https://github.com/Center-for-Living-Systems/biofile-finder)
(fork of the Allen Institute app) running on a lab workstation, serving Gardel Lab
microscopy datasets to a browser over self-signed HTTPS.

- **URL:** https://128.135.108.226/  (datasets list: https://128.135.108.226/datasets)
- **Access:** **PUBLIC — no login** (auth removed by operator decision). `/gardel` serves
  *only* files referenced by the dataset manifests (allowlist), not the whole NAS.
- **Host:** `lding-Dell-Pro-Max-Tower-T2-FCT2250` (`128.135.108.226`), Ubuntu.
- **Lives in:** `deploy/` inside this repo (scripts, generators, docs). The box deploys from `main`.
- **Credentials:** `deploy/.env` (gitignored; copy from `.env.example`). Consumed by `mount-nas.sh`.

> The app is **fully client-side** (DuckDB-WASM in the browser). There is no app
> backend/database to run. The server only serves static files + CSV manifests.

> The app is **fully client-side** (DuckDB-WASM in the browser). There is no app
> backend/database to run. The server only serves static files + CSV manifests.

---

## 1. How it works (architecture)

```
                          Browser (https, Basic Auth)
                                   │
                                   ▼
        ┌─────────────────────  Caddy  ─────────────────────┐
        │  128.135.108.226   tls internal + basic_auth      │
        │                                                   │
        │  /data/*   → /srv/shared        (manifests,       │
        │                                  previews, local  │
        │                                  datasets)        │
        │  /gardel/* → /srv/gardelnas     (NAS raw files,   │
        │                                  read-only mount) │
        │  /*        → /srv/www/biofile-finder              │
        │              (built app, SPA fallback to          │
        │               index.html)                         │
        └───────────────────────────────────────────────────┘
```

**Request flow for the datasets page**
1. Browser loads the static app from `/srv/www/biofile-finder` (`/datasets` route is
   served `index.html` via SPA fallback).
2. The app fetches the **master dataset list**: `https://128.135.108.226/data/Dataset+Manifest.csv`.
   (The bucket URL is baked into the build — see [§5](#5-how-the-app-was-modified).)
3. Each row is one dataset. Clicking it runs that row's `Specific query`, which loads
   the dataset's **file manifest** (e.g. `…/data/_derived/031125data-manifest.csv`).
4. The file manifest lists every file with a `File Path` URL (the openable file) and a
   `Thumbnail` URL (a generated PNG preview). DuckDB-WASM queries it in-browser for the
   filter/sort/grid UI.

**Two kinds of manifest — don't confuse them**
| Manifest | What it is | Headers must be… |
|----------|-----------|------------------|
| **Master** `Dataset+Manifest.csv` | the list shown on `/datasets` | **display labels**: `Dataset name`, `File Path`, `Featured`, `Specific query`, `Short description`, `File count`, `Size`, `Creation date`, … |
| **Per-dataset** `<id>-manifest.csv` | the files inside one dataset | `File Path`, `Thumbnail`, `File Name`, `File Size`, + any metadata facets (`Condition`, `Kind`, `Replicate`, …) |

The master-manifest headers are **display labels** because the app maps those columns by
their human label, not the machine name. Getting this wrong = an empty `/datasets` page.

**Previews:** CZI (Zeiss) and microscopy TIF do not render in a browser, so we generate a
512px max-projection **PNG preview** per image. Previews + manifests live on **local disk**
(`/srv/shared/_derived/`), never on the NAS (which is mounted read-only).

---

## 2. Where everything lives

| Path | Purpose | Served at |
|------|---------|-----------|
| `/srv/www/biofile-finder/` | the built app (static) | `/` |
| `/srv/shared/` | local datasets, manifests, previews | `/data/*` |
| `/srv/shared/Dataset+Manifest.csv` | master dataset list | `/data/Dataset+Manifest.csv` |
| `/srv/shared/_derived/` | generated previews + per-dataset manifests | `/data/_derived/*` |
| `/srv/gardelnas/` | **NAS** (`//psd-gardelnas.uchicago.edu/Expansion`, read-only) | `/gardel/*` |
| `/etc/caddy/Caddyfile` | reverse proxy / file server config | — |
| `/etc/gardelnas.cred` | NAS SMB credentials (mode 600, root) | — |
| `/home/dsadmin/biofile-finder/` | source checkout (rebuild here) | — |
| `~/biofile-finder/deploy/` | scripts, generators, `.venv`, tracking | — |

**Services (systemd):**
- `caddy` — the only thing serving traffic; auto-starts, auto-restarts. `systemctl status caddy`.
- `biofile-finder-demo` — the old synthetic-demo Python server, now **disabled** (replaced by Caddy static serving).

---

## 3. Security model

- **HTTPS:** Caddy `tls internal` (self-signed; no public DNS name exists for this box, so
  Let's Encrypt can't issue). Browsers warn unless Caddy's root CA is trusted on the client.
- **Auth:** HTTP Basic Auth at Caddy, single shared user. Protects the app *and* all files
  (`/data`, `/gardel`). This is the only access gate — the static app can't enforce auth itself.
- **Firewall:** `ufw` — inbound limited to 22 (SSH), 80, 443.
- **NAS:** mounted **read-only** (`ro`) with a dedicated read-only service account
  (`image_service`, no domain). Credentials only in `/etc/gardelnas.cred` (600).
- **Two independent layers:** the `researchers` OS group governs file reads on disk
  (Caddy is a member); Basic Auth governs web access. Adding someone to one does not grant the other.

⚠️ The box is on a **public IP** (`128.135.108.226`). Keep auth on. Do not switch to plain HTTP.

---

## 4. Common operations

### Add a NAS dataset to the app
```bash
cd ~/biofile-finder/deploy
# 1. generate previews + the per-dataset file manifest (reads files over SMB)
.venv/bin/python build-nas-dataset.py \
    --src "/srv/gardelnas/Annabel/FA-ML/.../<dataset folder>" \
    --id  "<short-slug>" \
    --name "<human label shown in the file view>"
# 2. add an entry to the DATASETS list in build-master-manifest.py, then:
python3 build-master-manifest.py        # regenerates /srv/shared/Dataset+Manifest.csv
```
No rebuild, no sudo. Hard-refresh `/datasets` to see it. (Raw files stream from the NAS via
`/gardel`; previews/manifest are local under `/data/_derived/`.)

### Add a LOCAL dataset (files copied to `/srv/shared`)
Use `build-shared-dataset.py` (same idea, files served from `/data` instead of `/gardel`),
then add a row in `build-master-manifest.py` and re-run it.

### Refresh an existing dataset (files changed on disk/NAS)
Re-run the same `build-*-dataset.py` command — it rebuilds previews + manifest.

### Managing logins
Basic Auth users live in `/etc/caddy/Caddyfile` under `basic_auth { }` as `user <bcrypt-hash>`.
```bash
caddy hash-password                        # type the new password -> prints a hash
sudoedit /etc/caddy/Caddyfile              # add/replace a `username <hash>` line
sudo systemctl reload caddy
```
It's a single shared credential set (no per-user accounts/roles). For real accounts/SSO you'd
front Caddy with an identity provider (Authelia/Authentik) — not set up.

### Remove the browser cert warning (per client machine)
Export Caddy's root CA and trust it on each machine:
```bash
sudo install -m644 /var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt \
    ~/biofile-finder/deploy/caddy-root-ca.crt
# copy to client, then trust (macOS: Keychain 'Always Trust'; Ubuntu: /usr/local/share/ca-certificates + update-ca-certificates; Windows: certutil -addstore -f Root)
```

### Rebuild the app (only needed for code/config changes)
```bash
cd /home/dsadmin/biofile-finder
npm --prefix packages/web run build
sudo rsync -a --delete packages/web/dist/ /srv/www/biofile-finder/
sudo chmod -R a+rX /srv/www/biofile-finder
sudo systemctl reload caddy
```

---

## 5. How the app was modified (vs. upstream)

These changes are in the source checkout `/home/dsadmin/biofile-finder/` and require a rebuild:

1. **`packages/core/constants/index.ts`** — `DatasetBucketUrl` (all environments) pointed at
   `https://128.135.108.226/data` instead of Allen's S3. This is where `/datasets` fetches
   `Dataset+Manifest.csv` from.
2. **`packages/web/webpack/index.html`** — removed Google Tag Manager (Allen analytics).
3. **`packages/web/src/components/Footer/index.tsx`** — removed the dead OneTrust "Cookie
   settings" button (its SDK isn't loaded in this build).

Unchanged app behavior worth knowing: the openable file column is `File Path` (or top-level
`file_path`); the thumbnail column is `Thumbnail`; values starting with `http`/`s3` are treated
as remote and opened in-browser.

---

## 6. NAS connection (reference)

- Share: `//psd-gardelnas.uchicago.edu/Expansion` → `/srv/gardelnas` (read-only, `_netdev,nofail`).
- Auth: username `image_service`, **no domain** (specifying `adlocal` causes `LOGON_FAILURE`).
  Credentials in `/etc/gardelnas.cred` (600, root). Mount defined in `/etc/fstab`.
- Mounted with `gid=researchers` so Caddy (a member) can read; `file_mode=0640,dir_mode=0750`.
- Remount after a reboot/outage: `sudo mount /srv/gardelnas` (auto-mounts on boot if NAS is up).

---

## 7. Scripts in this folder

| Script | What it does | Sudo? |
|--------|--------------|-------|
| `build-nas-dataset.py` | previews + file manifest for one NAS dataset folder | no |
| `build-shared-dataset.py` | same, for a local `/srv/shared` dataset | no |
| `build-master-manifest.py` | (re)generate the master `Dataset+Manifest.csv` from its `DATASETS` list | no |
| `serve-app-static.sh` | deploy build to `/srv/www` + Caddy static/SPA serving | yes |
| `add-data-route.sh` | add the `/data/*` Caddy route + grant Caddy NAS-group read | yes |
| `setup-caddy-auth.sh` | initial Caddy + Basic Auth + ufw hardening | yes |
| `provision.sh` | original end-to-end provisioner (reference) | yes |
| `demo-local.sh`, `demo-data-gen.py` | the old synthetic local demo (superseded) | no |

Work history / tasks are tracked in **beads** (`bd list`, `bd ready`) in `~/biofile-finder/deploy/.beads/`.

---

## 8. Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| `/datasets` is empty | Master manifest headers must be **display labels** (`Dataset name`, `File Path`, `Featured`, `Specific query`…). Regenerate with `build-master-manifest.py`. Hard-refresh. |
| A dataset opens but shows no files | The per-dataset manifest must have a `File Path` column with reachable URLs. Check `curl -k -u demo:PASS <File Path URL>` = 200. |
| No thumbnails | `Thumbnail` column URL must resolve (under `/data/_derived/…`). Re-run the dataset builder. |
| `/datasets` 404 | App not served with SPA fallback — re-run `serve-app-static.sh`. |
| Browser cert warning | Expected (self-signed). Trust the root CA (§4) or click through. |
| NAS files 404/403 | Check `mountpoint /srv/gardelnas`; remount with `sudo mount /srv/gardelnas`. Caddy must be in `researchers` group. |
| Empty page after a rebuild | Hard-refresh (Ctrl/Cmd-Shift-R) to drop the cached old JS bundle. |

Caddy logs: `journalctl -u caddy -f`.
