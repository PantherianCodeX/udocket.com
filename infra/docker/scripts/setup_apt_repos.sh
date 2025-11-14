#!/usr/bin/env bash
set -euo pipefail

# Idempotently configure Docker and GitHub CLI APT repositories
# and refresh apt indexes. Requires Python (available in python:*-slim).

install -m 0755 -d /etc/apt/keyrings
cache_dir="/tmp/cache-downloads"
mkdir -p "$cache_dir"

docker_key="$cache_dir/docker.gpg"
gh_key="$cache_dir/gh.gpg"

python - "$docker_key" <<'PY'
import sys,urllib.request
urllib.request.urlretrieve("https://download.docker.com/linux/debian/gpg", sys.argv[1])
PY
cp "$docker_key" /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

python - "$gh_key" <<'PY'
import sys,urllib.request
urllib.request.urlretrieve("https://cli.github.com/packages/githubcli-archive-keyring.gpg", sys.argv[1])
PY
cp "$gh_key" /etc/apt/keyrings/githubcli-archive-keyring.gpg
chmod a+r /etc/apt/keyrings/githubcli-archive-keyring.gpg

codename="$(. /etc/os-release && printf '%s' "$VERSION_CODENAME")"
arch="$(dpkg --print-architecture)"
echo "deb [arch=${arch} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian ${codename} stable" > /etc/apt/sources.list.d/docker.list
echo "deb [arch=${arch} signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list

# Refresh indexes only when needed: if lists are empty, or if no list files
# exist yet for the newly configured repos.
NEED_UPDATE=0
if [ -z "$(ls -A /var/lib/apt/lists 2>/dev/null || true)" ]; then
  NEED_UPDATE=1
fi
if ! ls /var/lib/apt/lists/*download.docker.com* >/dev/null 2>&1; then
  NEED_UPDATE=1
fi
if ! ls /var/lib/apt/lists/*cli.github.com* >/dev/null 2>&1; then
  NEED_UPDATE=1
fi

if [ "$NEED_UPDATE" = "1" ]; then
  apt-get update
fi
