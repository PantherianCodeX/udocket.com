# JSON Schemas

This directory hosts the canonical JSON Schema definitions that drive OpenAPI components, Pydantic model generation, and contract tests.

| Schema | Purpose |
| ------ | ------- |
| `api_error.schema.json` | Shared error envelope for all REST services. |
| `policy_context.schema.json` | Localization & Policy Engine response payload. |
| `locale.schema.json` | Locale pack describing CLDR/ICU resources and attribution. |
| `reference_bundle_manifest.schema.json` | Signed manifest for Reference Manager bundle releases. |
| `opa_discovery_manifest.schema.json` | Discovery manifest consumed by OPA evaluators (channels, bundles). |
| `opa_decision_log.schema.json` | Normalized decision log emitted by OPA sidecars. |
| `sse/event_envelope.schema.json` | SSE event envelope and payload definitions. |
| `log_record.schema.json` | Structured logging contract (`log_schema@1`). |

The build pipeline validates these schemas and regenerates strongly typed models for Python/TypeScript clients. Update schemas before modifying downstream models to keep the ecosystem in sync.
