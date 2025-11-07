# uDocket AI Runtime

This package is the canonical, exportable AI runtime for every agent and LangGraph
pipeline. It hosts the typed façade (`packages.ai.api`) plus the adapter registry and
policy guards that keep automation callers decoupled from provider SDKs.

## Layering

1. **API surface (`api.py`, `__init__.py`)** – dataclasses and Protocols that automation
   code consumes (`summarize`, `compose`, `extract_timeline`, …).
2. **Client implementations (`providers/`, `routing/`, `retrieval/`, `safety/`)** –
   strongly typed adapters that own all provider interactions, residency enforcement,
   moderation, and telemetry.
3. **Configuration (`config.py`, `settings/`)** – deterministic, typed settings loaders
   that resolve provider catalogs, capability limits, and residency policies.
4. **Support libraries (`compilers/`, `embeddings/`, `utils/`, `packaging/`)** –
   pure helpers for packaging, embeddings, promptsets, and structured compilers.

## Directory map

```text
packages/ai/
├─ api.py              # Typed façade + AIClient Protocols
├─ errors/             # Strongly typed error hierarchy
├─ providers/          # Adapter implementations, health checks, telemetry wiring
├─ routing/            # Route selection + capability enforcement
├─ retrieval/          # Vector/Semantic retrieval interfaces
├─ embeddings/         # Embedding model clients + DTOs
├─ safety/             # Moderation, egress/residency guards, prompt filters
├─ promptsets/         # Versioned prompt assets (per agent / locale)
├─ compilers/          # Structured compilers (timeline/entity normalizers)
├─ config.py           # AISettings dataclasses + loaders
├─ settings/           # Declarative defaults + schemas
├─ utils/              # Small pure helpers with strict typing
└─ py.typed            # Package ships typing information
```

Refer to `docs/overview/tdd/appendices/repository_trees.md` for binding layout details.

## Invariants

- All DTOs (`api.py`) are frozen dataclasses with `slots=True` and strictly typed IDs.
- Providers implement the `ProviderAdapter` protocol in `providers/interfaces.py`; they
  must report residency (`region`) and supported tasks.
- The default client (`packages.ai.client.DefaultAIClient`) enforces residency and
  egress policy guards before invoking a provider.
- Telemetry payloads (`packages.ai.telemetry`) are immutable and JSON-serializable via
  the shared helpers in `packages.ai.utils`.
