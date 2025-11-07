# syntax=docker/dockerfile:1.7
FROM python:3.12-slim-bookworm AS base

ARG VALE_VERSION=3.7.1

ENV PIP_NO_CACHE_DIR=0 \
    UV_COMPILE_BYTECODE=0 \
    UV_LINK_MODE=copy \
    PATH="/root/.cargo/bin:${PATH}" \
    PUPPETEER_SKIP_DOWNLOAD=1 \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /udocket

# Core system dependencies for docs tooling.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      ca-certificates \
      chromium \
      curl \
      fonts-dejavu \
      git \
      pandoc

# Install Node.js (for mermaid CLI and markdownlint).
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,target=/tmp/nodesource-cache,sharing=locked \
    set -eux; \
    cache_dir=/tmp/nodesource-cache; \
    mkdir -p "$cache_dir"; \
    script="$cache_dir/setup_20.x.sh"; \
    if [ ! -f "$script" ]; then \
      curl -fsSL https://deb.nodesource.com/setup_20.x -o "$script"; \
    fi; \
    bash "$script"; \
    apt-get update; \
    apt-get install -y --no-install-recommends nodejs

# Install Vale (style checker) for Markdown linting.
RUN --mount=type=cache,target=/tmp/vale-cache,sharing=locked <<'EOF'
set -eux
arch="$(dpkg --print-architecture)"
case "$arch" in
  amd64) vale_asset="vale_${VALE_VERSION}_Linux_64-bit.tar.gz" ;;
  arm64) vale_asset="vale_${VALE_VERSION}_Linux_arm64.tar.gz" ;;
  *) echo "Unsupported architecture: $arch" >&2; exit 1 ;;
esac
cache_dir="/tmp/vale-cache"
mkdir -p "$cache_dir"
archive="$cache_dir/${vale_asset}"
if [ ! -f "$archive" ]; then
  curl -fsSL "https://github.com/errata-ai/vale/releases/download/v${VALE_VERSION}/${vale_asset}" -o "$archive"
fi
tmpdir="$(mktemp -d)"
tar -xzf "$archive" -C "$tmpdir" vale
install -m 0755 "$tmpdir/vale" /usr/local/bin/vale
rm -rf "$tmpdir"
EOF

# Install uv globally (cache installer script for repeat builds).
RUN --mount=type=cache,target=/root/.cache/uv-installer,sharing=locked <<'EOF'
set -eux
cache_dir="/root/.cache/uv-installer"
mkdir -p "$cache_dir"
script="$cache_dir/install.sh"
if [ ! -f "$script" ]; then
  curl -fsSL https://astral.sh/uv/install.sh -o "$script"
fi
UV_INSTALL_DIR=/usr/local/bin sh "$script"
EOF

# Copy dependency metadata first to maximise cache hits.
COPY packages/docs_tooling/pyproject.toml packages/docs_tooling/pyproject.toml
COPY packages/docs_tooling/uv.lock packages/docs_tooling/uv.lock
COPY packages/docs_tooling/package.json packages/docs_tooling/package.json
COPY packages/docs_tooling/package-lock.json packages/docs_tooling/package-lock.json
COPY packages/docs_tooling/README.md packages/docs_tooling/README.md
COPY packages/docs_tooling/src packages/docs_tooling/src
COPY packages/docs_tooling/plugins packages/docs_tooling/plugins

# Install Python deps into the default uv-managed virtual environment (project omitted for now).
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen --extra dev --no-install-project --project packages/docs_tooling

# Install Node tooling.
RUN --mount=type=cache,target=/root/.npm,sharing=locked \
    if [ -f packages/docs_tooling/package-lock.json ]; then (cd packages/docs_tooling && npm ci); fi

# Copy the remaining repository context.
COPY . .

# Install project itself now that sources are present.
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen --extra dev --project packages/docs_tooling

# Install local MkDocs plugins (editable) for development workflows.
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv pip install --python packages/docs_tooling/.venv/bin/python -e packages/docs_tooling/plugins/udocket_mkdocs_plugins

ENV VIRTUAL_ENV=/udocket/packages/docs_tooling/.venv
ENV PATH="/udocket/packages/docs_tooling/.venv/bin:${PATH}"

CMD ["bash"]
