#!/usr/bin/env bash
#
# Harden the demo: ufw + Caddy (HTTPS, self-signed) + Basic Auth in front.
#
#   sudo bash ~/biofile-finder/deploy/setup-caddy-auth.sh
#
# After this: the only public ports are 22/80/443. The Python demo backend is
# rebound to loopback (127.0.0.1:8080) and reached only via Caddy, which adds
# TLS + a username/password prompt.
#
set -euo pipefail

IP=128.135.108.226
BACKEND=127.0.0.1:8080
UNIT_SRC=/home/dsadmin/biofile-finder/deploy/biofile-finder-demo.service

say(){ printf '\n\033[1;36m== %s\033[0m\n' "$*"; }
ok(){  printf '   \033[32m✓ %s\033[0m\n' "$*"; }

[ "$(id -u)" -eq 0 ] || { echo "Run me with sudo."; exit 1; }

# ---------------------------------------------------------------- 1) Install Caddy
say "1) Install Caddy"
if ! command -v caddy >/dev/null 2>&1; then
  apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl gnupg
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt \
    > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -qq
  apt-get install -y caddy
  ok "caddy installed ($(caddy version))"
else
  ok "caddy already installed ($(caddy version))"
fi

# --------------------------------------------------- 2) Rebind backend to loopback
say "2) Rebind demo backend to loopback + point manifest at Caddy"
cp "$UNIT_SRC" /etc/systemd/system/biofile-finder-demo.service
systemctl daemon-reload
systemctl restart biofile-finder-demo
sleep 1
if ss -ltn | grep -q '127.0.0.1:8080'; then ok "backend now on 127.0.0.1:8080"; else
  echo "   ⚠ backend not on loopback yet — check: journalctl -u biofile-finder-demo -n20"; fi

# ------------------------------------------------------------- 3) Basic Auth creds
say "3) Set the login (Basic Auth)"
read -rp "   Auth username: " AUTH_USER
read -rsp "   Auth password: " AUTH_PASS; echo
read -rsp "   Confirm password: " AUTH_PASS2; echo
[ "$AUTH_PASS" = "$AUTH_PASS2" ] || { echo "   passwords do not match"; exit 1; }
HASH="$(printf '%s\n' "$AUTH_PASS" | caddy hash-password)"
ok "password hashed (bcrypt)"

# ------------------------------------------------------------------ 4) Caddyfile
say "4) Write /etc/caddy/Caddyfile (TLS internal + Basic Auth + reverse_proxy)"
cat > /etc/caddy/Caddyfile <<EOF
# BioFile Finder demo — self-signed HTTPS, password-protected, proxied to the
# loopback Python backend. Browsers warn about the cert until the Caddy local
# CA root is trusted (see post-run note).
$IP {
    tls internal
    basic_auth {
        $AUTH_USER $HASH
    }
    reverse_proxy $BACKEND
}
EOF
caddy validate --config /etc/caddy/Caddyfile && ok "Caddyfile valid"
systemctl enable --now caddy
systemctl reload caddy 2>/dev/null || systemctl restart caddy
ok "caddy running (serving 443, redirecting 80)"

# --------------------------------------------------------------------- 5) Firewall
say "5) Enable ufw (default-deny inbound; allow SSH/80/443)"
ufw allow OpenSSH        >/dev/null 2>&1 || ufw allow 22/tcp >/dev/null 2>&1 || true
ufw allow 80/tcp         >/dev/null 2>&1 || true
ufw allow 443/tcp        >/dev/null 2>&1 || true
ufw delete allow 8080/tcp >/dev/null 2>&1 || true   # backend is loopback now
ufw default deny incoming  >/dev/null 2>&1 || true
ufw default allow outgoing >/dev/null 2>&1 || true
ufw --force enable
ok "ufw enabled — only 22/80/443 inbound"
ufw status numbered | sed 's/^/   /'

# --------------------------------------------------------------------- 6) Summary
say "Done"
cat <<EOF
   URL:        https://$IP/        (login with the username/password you set)
   Data source: https://$IP/nas/manifest.csv
   Backend:    $BACKEND (loopback only, via Caddy)

   The cert is self-signed by Caddy's internal CA, so browsers show a warning.
   To remove the warning, trust this root CA on each client machine:
     /var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt

   To revert exposure entirely: sudo systemctl disable --now caddy biofile-finder-demo
EOF
