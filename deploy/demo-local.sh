#!/usr/bin/env bash
#
# Run BioFile Finder as a fully LOCAL demo — no NAS, no sudo, no Caddy.
# Generates a synthetic dataset, serves the app + the files together, and
# prints the URL + the manifest URL to load in the app's "add data source".
#
#   bash ~/biofile-finder/deploy/demo-local.sh          # serve on :8080
#   PORT=9000 bash ~/biofile-finder/deploy/demo-local.sh
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${PORT:-8080}"
BIND="${BIND:-127.0.0.1}"          # set BIND=0.0.0.0 to expose on the network
HOST="${HOST:-localhost}"          # host clients use in their browser; must match manifest URLs
# Manifest base URL. When behind Caddy, set PUBLIC_BASE_URL=https://<host>/nas
# so File Path links point at Caddy (443), not the loopback backend.
BASE_URL="${PUBLIC_BASE_URL:-http://${HOST}:${PORT}/nas}"

# Locate the built app (dist/) wherever the repo currently lives.
DIST=""
for c in /home/bff/biofile-finder/packages/web/dist \
         /home/dsadmin/biofile-finder/packages/web/dist; do
  [ -f "$c/index.html" ] && DIST="$c" && break
done
[ -n "$DIST" ] || { echo "Could not find a built dist/ — run the web build first."; exit 1; }
echo "Using app build: $DIST"

DATA="$HERE/demo-data"
WEBROOT="$HERE/demo-web-root"

# 1) Generate the synthetic dataset + manifest (always refresh).
python3 "$HERE/demo-data-gen.py" --root "$DATA" --base-url "$BASE_URL"

# 2) Assemble a web root: app at /, demo files at /nas, manifest at /nas/manifest.csv
rm -rf "$WEBROOT"; mkdir -p "$WEBROOT"
for f in "$DIST"/*; do ln -s "$f" "$WEBROOT/$(basename "$f")"; done
ln -s "$DATA" "$WEBROOT/nas"

cat <<EOF

────────────────────────────────────────────────────────────────────
  BioFile Finder demo is starting on  http://${HOST}:${PORT}/  (bind ${BIND})
────────────────────────────────────────────────────────────────────
  In the app: "+ Add Data Source"  →  load this URL:
      ${BASE_URL}/manifest.csv
  (or upload the file directly: ${DATA}/manifest.csv)

  Then browse/filter by Plate, Well, Condition, Channel, Timepoint.
  Click an image row to preview it (served from /nas/...).

  Remote box? From your laptop:  ssh -L ${PORT}:localhost:${PORT} dsadmin@<box>
  Stop the demo:  Ctrl-C
────────────────────────────────────────────────────────────────────

EOF

# 3) Serve (foreground; Ctrl-C to stop).
cd "$WEBROOT"
exec python3 -m http.server "$PORT" --bind "$BIND"
