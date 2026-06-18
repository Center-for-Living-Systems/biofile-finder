#!/usr/bin/env bash
#
# BioFile Finder — deployment provisioner (run with sudo).
#
#   sudo bash ~/biofile-finder/deploy/provision.sh
#
# Idempotent: safe to re-run. Each step checks its own state and skips if done.
# Steps map to beads bff-ehm (A), bff-xwr (C), bff-2zw (D), bff-05i (F).
# It will PROMPT for the NAS host/share/credentials (step C) unless you pass them
# as environment variables:
#   NAS_HOST=nas.example.org NAS_SHARE=images NAS_USER=svc NAS_PASS=... NAS_DOMAIN=WORKGROUP \
#     sudo -E bash provision.sh
#
set -euo pipefail

SRC_REPO=/home/dsadmin/biofile-finder
DST_REPO=/home/bff/biofile-finder
DIST="$DST_REPO/packages/web/dist"
HOSTNAME_FQDN="lding-Dell-Pro-Max-Tower-T2-FCT2250"
HOST_IP="128.135.108.226"
CRED=/etc/biofile-finder-smb.cred
NAS_MNT=/srv/nas

say(){ printf '\n\033[1;36m== %s\033[0m\n' "$*"; }
ok(){  printf '   \033[32m✓ %s\033[0m\n' "$*"; }
skip(){ printf '   \033[33m• %s (already done, skipping)\033[0m\n' "$*"; }

[ "$(id -u)" -eq 0 ] || { echo "Run me with sudo."; exit 1; }
id bff >/dev/null 2>&1 || { echo "bff user missing — create it first."; exit 1; }

# ---------------------------------------------------------------- A: re-home repo
say "A) Re-home repo to $DST_REPO (owned by bff)"
if [ -f "$DIST/index.html" ]; then
  skip "$DIST already present"
else
  [ -d "$SRC_REPO" ] || { echo "source repo $SRC_REPO not found"; exit 1; }
  install -d -o bff -g bff /home/bff
  rsync -a --chown=bff:bff "$SRC_REPO"/ "$DST_REPO"/
  sudo -u bff bash -c "cd '$DST_REPO' && git status -s >/dev/null 2>&1 || true"
  [ -f "$DIST/index.html" ] || { echo "re-home failed: no dist/index.html"; exit 1; }
  ok "repo copied to $DST_REPO and owned by bff"
  echo "   (source left at $SRC_REPO — remove manually once happy: rm -rf $SRC_REPO)"
fi

# ----------------------------------------------------------- C: cifs + NAS mount
say "C) Install cifs-utils + mount NAS read-only at $NAS_MNT"
dpkg -s cifs-utils >/dev/null 2>&1 && skip "cifs-utils installed" || { apt-get update -qq; apt-get install -y cifs-utils; ok "cifs-utils installed"; }
install -d "$NAS_MNT"

if [ -f "$CRED" ]; then
  skip "credentials file $CRED exists"
else
  : "${NAS_USER:=}"; : "${NAS_PASS:=}"; : "${NAS_DOMAIN:=}"
  [ -n "$NAS_USER" ] || read -rp "   SMB username: " NAS_USER
  [ -n "$NAS_PASS" ] || { read -rsp "   SMB password: " NAS_PASS; echo; }
  [ -n "$NAS_DOMAIN" ] || read -rp "   SMB domain/workgroup (blank if none): " NAS_DOMAIN
  umask 077
  { echo "username=$NAS_USER"; echo "password=$NAS_PASS"; [ -n "$NAS_DOMAIN" ] && echo "domain=$NAS_DOMAIN"; } > "$CRED"
  chmod 600 "$CRED"
  ok "wrote $CRED (mode 600)"
fi

: "${NAS_HOST:=}"; : "${NAS_SHARE:=}"
[ -n "$NAS_HOST" ]  || read -rp "   NAS host (e.g. nas.example.org or 10.0.0.5): " NAS_HOST
[ -n "$NAS_SHARE" ] || read -rp "   NAS share name (e.g. images): " NAS_SHARE
FSTAB_LINE="//$NAS_HOST/$NAS_SHARE $NAS_MNT cifs credentials=$CRED,uid=bff,gid=bff,ro,vers=3.0,_netdev,nofail 0 0"
if grep -qsF "$NAS_MNT cifs" /etc/fstab; then
  skip "fstab already has a $NAS_MNT entry"
else
  printf '%s\n' "$FSTAB_LINE" >> /etc/fstab
  ok "added fstab line for //$NAS_HOST/$NAS_SHARE"
fi
if mountpoint -q "$NAS_MNT"; then
  skip "$NAS_MNT already mounted"
else
  mount "$NAS_MNT" && ok "mounted $NAS_MNT" || echo "   ⚠ mount failed — check NAS host/share/creds, then: sudo mount $NAS_MNT"
fi

# --------------------------------------------------------------- D: Caddy + TLS
say "D) Install Caddy with self-signed TLS"
if ! command -v caddy >/dev/null 2>&1; then
  apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl gnupg
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -qq
  apt-get install -y caddy
  ok "caddy installed"
else
  skip "caddy installed"
fi

cat > /etc/caddy/Caddyfile <<EOF
$HOSTNAME_FQDN, $HOST_IP {
    tls internal
    handle_path /nas/* {
        root * $NAS_MNT
        file_server
    }
    handle {
        root * $DIST
        file_server
        try_files {path} /index.html
    }
}
EOF
ok "wrote /etc/caddy/Caddyfile"
# caddy user must be able to read bff's dist + the NAS mount
usermod -aG bff caddy 2>/dev/null || true
chmod o+rx /home/bff 2>/dev/null || true
caddy validate --config /etc/caddy/Caddyfile && ok "Caddyfile valid"
systemctl enable --now caddy
systemctl reload caddy 2>/dev/null || systemctl restart caddy
ok "caddy running"

# ------------------------------------------------------------------ F: hardening
say "F) Hardening (firewall, unattended-upgrades, sshd)"
if command -v ufw >/dev/null 2>&1; then
  ufw allow OpenSSH    >/dev/null 2>&1 || ufw allow 22/tcp  >/dev/null 2>&1 || true
  ufw allow 80/tcp     >/dev/null 2>&1 || true
  ufw allow 443/tcp    >/dev/null 2>&1 || true
  yes | ufw enable     >/dev/null 2>&1 || true
  ok "ufw: allowed 22/80/443"
else
  echo "   • ufw not installed — skipping firewall (install with: apt-get install ufw)"
fi
apt-get install -y unattended-upgrades >/dev/null 2>&1 && ok "unattended-upgrades installed" || true
dpkg-reconfigure -f noninteractive unattended-upgrades >/dev/null 2>&1 || true
if grep -qsE '^\s*#?\s*PasswordAuthentication' /etc/ssh/sshd_config; then
  sed -i 's/^\s*#\?\s*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
  systemctl reload ssh 2>/dev/null || systemctl reload sshd 2>/dev/null || true
  ok "sshd: PasswordAuthentication no"
fi
echo
echo "   To trust HTTPS without warnings, copy Caddy's root CA to clients:"
echo "     /var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt"

say "Done. Next:  sudo -u bff -i  then  bash ~/biofile-finder/deploy/make-manifest.sh"
echo "Then browse:  https://$HOSTNAME_FQDN/   (or https://$HOST_IP/)"
