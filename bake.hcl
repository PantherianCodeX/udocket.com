# Buildx Bake configuration for uDocket images

group "default" {
  targets = ["platform", "docs", "keycloak"]
}

target "common" {
  # Default to a single platform; add linux/arm64 if needed
  platforms = ["linux/amd64"]
}

target "platform" {
  inherits   = ["common"]
  context    = "."
  dockerfile = "infra/docker/Dockerfile.platform"
  cache-from = ["type=local,src=.docker/buildx-cache/platform"]
  cache-to   = ["type=local,dest=.docker/buildx-cache/platform,mode=max"]
}

target "docs" {
  inherits   = ["common"]
  context    = "."
  dockerfile = "packages/docs_tooling/Dockerfile"
  cache-from = ["type=local,src=.docker/buildx-cache/docs"]
  cache-to   = ["type=local,dest=.docker/buildx-cache/docs,mode=max"]
}

target "keycloak" {
  inherits   = ["common"]
  context    = "."
  dockerfile = "infra/docker/Dockerfile.keycloak"
  cache-from = ["type=local,src=.docker/buildx-cache/keycloak"]
  cache-to   = ["type=local,dest=.docker/buildx-cache/keycloak,mode=max"]
}

# Optional: warm dev toolchain stage cache used by the devcontainer
group "cache-warm" {
  targets = ["platform-dev-toolchain"]
}

target "platform-dev-toolchain" {
  inherits   = ["common"]
  context    = "."
  dockerfile = "infra/docker/Dockerfile.platform"
  target     = "toolchain"
  args = {
    DEV_TOOLS = "1"
  }
  cache-from = ["type=local,src=.docker/buildx-cache/platform-dev"]
  cache-to   = ["type=local,dest=.docker/buildx-cache/platform-dev,mode=max"]
  # No tags/outputs: used for cache priming only
}
