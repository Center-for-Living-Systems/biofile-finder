#!/usr/bin/env bash
#
# Serve the built app directly from Caddy with SPA fallback, so client routes
# (/datasets, /app, deep links) work instead of 404-ing. Replaces the Python
# http.server backend. Keeps Basic Auth + the /data route untouched.
#
#   sudo bash ~/biofile-finder/deploy/serve-app-static.sh
#
set -euo pipefail
CF=/etc/caddy/Caddyfile
DIST=/home/dsadmin/biofile-finder/packages/web/dist
WEBROOT=/srv/www/biofile-finder

ok(){ printf '   \033[32m✓ %s\033[0m\n' "$*"; }
[ "$(id -u)" -eq 0 ] || { echo "Run me with sudo."; exit 1; }
[ -f "$DIST/index.html" ] || { echo "no built app at $DIST"; exit 1; }

# 1) Deploy the build to a caddy-readable location (home dirs aren't traversable by caddy)
install -d "$WEBROOT"
rsync -a --delete "$DIST"/ "$WEBROOT"/
chmod -R a+rX "$WEBROOT"
ok "deployed app to $WEBROOT (world-readable)"

# 2) Swap the reverse_proxy backend for static file serving + SPA fallback
if grep -q "root \* $WEBROOT" "$CF"; then
  ok "Caddyfile already serving static app — skipping edit"
else
  cp "$CF" "$CF.bak.prestatic"
  python3 - "$CF" "$WEBROOT" <<'PY'
import sys
cf, webroot = sys.argv[1], sys.argv[2]
src = open(cf).read()
needle = "reverse_proxy 127.0.0.1:8080"
assert needle in src, "reverse_proxy line not found"
repl = (f"root * {webroot}\n"
        "        try_files {path} /index.html\n"
        "        file_server")
open(cf, "w").write(src.replace(needle, repl, 1))
print("   replaced reverse_proxy with static file_server + try_files fallback")
PY
  ok "Caddyfile updated (backup: $CF.bak.prestatic)"
fi

# 3) Retire the Python demo backend (no longer needed)
systemctl disable --now biofile-finder-demo 2>/dev/null && ok "stopped/disabled biofile-finder-demo" || true

# 4) Validate + reload
caddy fmt --overwrite "$CF" >/dev/null 2>&1 || true
caddy validate --config "$CF" && ok "Caddyfile valid"
systemctl reload caddy
ok "caddy reloaded"

cat <<EOF

Done. Verify (swap in your password):
  curl -sk -u demo:PASS -o /dev/null -w "/datasets        %{http_code}\\n" https://128.135.108.226/datasets
  curl -sk -u demo:PASS -o /dev/null -w "master manifest  %{http_code}\\n" "https://128.135.108.226/data/Dataset+Manifest.csv"
  curl -sk -u demo:PASS -o /dev/null -w "app index        %{http_code}\\n" https://128.135.108.226/

Then open:  https://128.135.108.226/datasets   ->  '031125data' should be listed.
EOF
