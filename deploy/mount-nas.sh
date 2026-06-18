#!/usr/bin/env bash
#
# Mount the NAS read-only using credentials from deploy/.env. Run with sudo.
#   sudo bash deploy/mount-nas.sh
#
# Reads NAS_* from .env, writes /etc/gardelnas.cred (600, root), ensures the
# fstab entry, and mounts. Idempotent.
#
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$HERE/.env" ] || { echo "missing $HERE/.env (copy from .env.example)"; exit 1; }
set -a; . "$HERE/.env"; set +a
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }
: "${NAS_HOST:?}"; : "${NAS_SHARE:?}"; : "${NAS_USER:?}"; : "${NAS_PASS:?}"; : "${NAS_MOUNT:?}"

CRED=/etc/gardelnas.cred
umask 077
{ echo "username=$NAS_USER"; echo "password=$NAS_PASS"; [ -n "${NAS_DOMAIN:-}" ] && echo "domain=$NAS_DOMAIN"; } > "$CRED"
chmod 600 "$CRED"; chown root:root "$CRED"
echo "  wrote $CRED (600)"

install -d "$NAS_MOUNT"
LINE="//${NAS_HOST}/${NAS_SHARE} ${NAS_MOUNT} cifs credentials=${CRED},uid=dsadmin,gid=researchers,ro,vers=3.0,_netdev,nofail,dir_mode=0750,file_mode=0640 0 0"
if grep -q " ${NAS_MOUNT} cifs " /etc/fstab; then echo "  fstab entry exists"; else echo "$LINE" >> /etc/fstab; echo "  added fstab entry"; fi

if mountpoint -q "$NAS_MOUNT"; then echo "  already mounted"; else mount "$NAS_MOUNT" && echo "  mounted $NAS_MOUNT"; fi
ls "$NAS_MOUNT" >/dev/null 2>&1 && echo "  ✓ $NAS_MOUNT readable" || echo "  ⚠ cannot list $NAS_MOUNT"
