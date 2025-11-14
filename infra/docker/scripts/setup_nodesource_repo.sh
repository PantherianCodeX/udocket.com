#!/usr/bin/env bash
set -euo pipefail

MAJOR="${1:-20}"
ARCH="$(dpkg --print-architecture)"
CODENAME="$(. /etc/os-release && printf '%s' "$VERSION_CODENAME")"

install -m 0755 -d /etc/apt/keyrings
CACHE_DIR="/tmp/cache-downloads"
mkdir -p "$CACHE_DIR"

KEYRING="/etc/apt/keyrings/nodesource.gpg"
KEYTMP="$CACHE_DIR/nodesource-${MAJOR}.gpg"

# download the current NodeSource key (correct URL)
curl -fsSL "https://deb.nodesource.com/gpgkey/nodesource.gpg.key" -o "$KEYTMP"

# dearmor to binary .gpg if gpg available; otherwise copy (but we prefer gpg)
if command -v gpg >/dev/null 2>&1; then
  gpg --batch --yes --dearmor -o "$KEYRING" "$KEYTMP"
else
  cp "$KEYTMP" "$KEYRING"
fi
chmod a+r "$KEYRING"

cat > /etc/apt/sources.list.d/nodesource.list <<EOF
deb [arch=${ARCH} signed-by=${KEYRING}] https://deb.nodesource.com/node_${MAJOR}.x ${CODENAME} main
EOF

# Refresh indexes only when NodeSource lists are missing (or lists are empty)
NEED_UPDATE=0
if [ -z "$(ls -A /var/lib/apt/lists 2>/dev/null || true)" ]; then
  NEED_UPDATE=1
fi
if ! ls /var/lib/apt/lists/*deb.nodesource.com* >/dev/null 2>&1; then
  NEED_UPDATE=1
fi

if [ "$NEED_UPDATE" = "1" ]; then
  apt-get update
fi
