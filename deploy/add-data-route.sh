#!/usr/bin/env bash
#
# Serve /srv/shared through Caddy at /data/* (behind the existing Basic Auth),
# so the real 031125data files + generated previews are reachable by the app.
#
#   sudo bash ~/biofile-finder/deploy/add-data-route.sh
#
# Idempotent. Preserves the existing basic_auth block untouched.
#
set -euo pipefail
CF=/etc/caddy/Caddyfile
DATA=/srv/shared

say(){ printf '\n\033[1;36m== %s\033[0m\n' "$*"; }
ok(){  printf '   \033[32m✓ %s\033[0m\n' "$*"; }
[ "$(id -u)" -eq 0 ] || { echo "Run me with sudo."; exit 1; }

# 1) Let the caddy user read the files (group is 'researchers', dir is setgid 2775)
say "1) Grant caddy read access to $DATA"
usermod -aG researchers caddy
chmod -R g+rX "$DATA"
ok "caddy added to 'researchers'; group-read ensured on $DATA"

# 2) Insert the /data file_server handler, wrapping the existing reverse_proxy.
say "2) Add /data/* route to $CF (preserving basic_auth)"
if grep -q "handle_path /data/\*" "$CF"; then
  ok "/data route already present — skipping edit"
else
  cp "$CF" "$CF.bak.predata"
  python3 - "$CF" "$DATA" <<'PY'
import sys
cf, data = sys.argv[1], sys.argv[2]
src = open(cf).read()
needle = "reverse_proxy 127.0.0.1:8080"
assert needle in src, "expected reverse_proxy line not found in Caddyfile"
block = (
    "handle_path /data/* {\n"
    f"        root * {data}\n"
    "        file_server {\n"
    "            browse\n"
    "        }\n"
    "    }\n"
    "    handle {\n"
    f"        {needle}\n"
    "    }"
)
open(cf, "w").write(src.replace(needle, block, 1))
print("   rewrote reverse_proxy into handle_path /data/* + handle {}")
PY
  ok "/data route added (backup: $CF.bak.predata)"
fi

# 3) Validate + restart (restart, not reload, so caddy picks up the new group)
say "3) Validate + restart Caddy"
caddy fmt --overwrite "$CF" >/dev/null 2>&1 || true
caddy validate --config "$CF" && ok "Caddyfile valid"
systemctl restart caddy
ok "caddy restarted (new group membership active)"

say "Done"
cat <<EOF
   In the app (https://128.135.108.226/, after login):
     + Add Data Source  ->  https://128.135.108.226/data/_derived/031125data-manifest.csv

   Quick check (swap in your password):
     curl -sk -u demo:PASS -o /dev/null -w "manifest %{http_code}\\n" \\
       https://128.135.108.226/data/_derived/031125data-manifest.csv
     curl -sk -u demo:PASS -o /dev/null -w "a czi   %{http_code}\\n" \\
       "https://128.135.108.226/data/031125data/Ycomp/$(ls /srv/shared/031125data/Ycomp | grep -m1 '\\.czi$' | sed 's/ /%20/g')"
EOF
