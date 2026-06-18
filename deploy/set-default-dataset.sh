#!/usr/bin/env bash
#
# Make the 031125data manifest auto-load for EVERY user who opens the site.
# Adds a Caddy redirect: bare https://128.135.108.226/  ->  /?source=<manifest>
# so nobody has to "Add Data Source" by hand. Idempotent; preserves auth + /data.
#
#   sudo bash ~/biofile-finder/deploy/set-default-dataset.sh
#
set -euo pipefail
CF=/etc/caddy/Caddyfile
ENC='source=%7B%22name%22%3A%22031125data%22%2C%22type%22%3A%22csv%22%2C%22uri%22%3A%22https%3A%2F%2F128.135.108.226%2Fdata%2F_derived%2F031125data-manifest.csv%22%7D'

ok(){ printf '   \033[32m✓ %s\033[0m\n' "$*"; }
[ "$(id -u)" -eq 0 ] || { echo "Run me with sudo."; exit 1; }

if grep -q "@needsSource" "$CF"; then
  ok "default-dataset redirect already present — refreshing target"
  # replace the existing redir target line in case the manifest URL changed
  sed -i "s|redir @needsSource /?source=[^ ]* 302|redir @needsSource /?${ENC} 302|" "$CF"
else
  cp "$CF" "$CF.bak.predefault"
  # Insert the matcher + redirect just before the first handler block.
  python3 - "$CF" "$ENC" <<'PY'
import sys
cf, enc = sys.argv[1], sys.argv[2]
src = open(cf).read()
anchor = "handle_path /data/*"
assert anchor in src, "expected /data route not found — run add-data-route.sh first"
snippet = (
    "@needsSource {\n"
    "        path /\n"
    "        not query source=*\n"
    "    }\n"
    f"    redir @needsSource /?{enc} 302\n\n    "
)
open(cf, "w").write(src.replace(anchor, snippet + anchor, 1))
print("   inserted @needsSource redirect before the /data route")
PY
  ok "redirect added (backup: $CF.bak.predefault)"
fi

caddy fmt --overwrite "$CF" >/dev/null 2>&1 || true
caddy validate --config "$CF" && ok "Caddyfile valid"
systemctl reload caddy
ok "caddy reloaded"
echo
echo "Now: https://128.135.108.226/  auto-loads 031125data for everyone (after login)."
echo "Test:  curl -sk -u demo:PASS -o /dev/null -w '%{http_code} %{redirect_url}\\n' https://128.135.108.226/"
