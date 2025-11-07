---
title: "uDocket — TDD Appendix: Repository Trees"
subtitle: "Canonical service and package layout vision"
authors:
  - "Platform Architecture Team"
version: "0.1-draft"
status: implementable
classification: Confidential
last_updated: "2025-10-30"
updated_by: "Documentation Team"
owners:
  - "Platform Architecture"
reviewers:
  - "Platform Engineering"
approvers:
  - "Architecture Steering Committee"
approved_by:
approved_date:
---

______________________________________________________________________

## Document Controls

<!-- BEGIN AUTO-GENERATED: document-controls -->
| Field | Value |
| --- | --- |
| Authors | Platform Architecture Team |
| Version | 0.1-draft |
| Status | implementable |
| Classification | Confidential |
| Last updated | 2025-10-30 |
| Updated by | Documentation Team |
| Owners | Platform Architecture |
| Reviewers | Platform Engineering |
| Approvers | Architecture Steering Committee |
| Approved by | |
| Approved date | |
<!-- END AUTO-GENERATED: document-controls -->

______________________________________________________________________

## Appendix overview

This appendix captures the canonical repository trees that each service area must target.
Treat these as the design north star during large refactors: the LangGraph agents, web
applications, and operational tooling all land under the directories listed here.
The sections are ordered from the shared platform runtime outward through automation,
packages, experience, data, infrastructure, testing, and documentation. Update this
appendix manually whenever the canonical structure changes.

**Tree Index**

- [A. Platform runtime & core services](#a-platform-runtime-core-services)
- [B. Automation & agent pipelines](#b-automation-agent-pipelines)
- [C. Shared packages & SDKs](#c-shared-packages-sdks)
- [D. Experience & communications](#d-experience-communications)
- [E. Data, trust & compliance](#e-data-trust-compliance)
- [F. Infrastructure & operations](#f-infrastructure-operations)
- [G. Testing & quality](#g-testing-quality)
- [H. Documentation system](#h-documentation-system)


______________________________________________________________________

### A. Platform runtime & core services {#a-platform-runtime-core-services}

The platform runtime is split into web apps under `apps/` and independent services under
`services/`, making each deployable obvious and auditable.

```tree
apps/
  web/
  channels/
  portal/
  jobs/
services/
  guardian/
  digital-signer/
  settings/
  localization-policy-engine/
  reference-manager/
  notifications/
  worker-cluster/
  llm-registry/
  speech-registry/
  storage-adapters/
  assistants-gateway/
  guardian-quarantine/
```

### B. Automation & agent pipelines {#b-automation-agent-pipelines}

Automation code is layered so LangGraph pipelines, agent implementations, and Celery task
modules remain isolated yet composable.

```tree
automation/
  langgraph/
  pipelines/
  agents/
    transcribe/
    analyze/
    compose/
    timeline/
    relationship/
  task-modules/
```

### C. Shared packages & SDKs {#c-shared-packages-sdks}

Packages house reusable primitives, policy-bound orchestration, AI tooling, docs helpers,
and customer SDKs.

```tree
packages/
  udocket_common/
  udocket_core/
    guardian/
    lpe/
    llm/
    failover/
    reference_manager/
    redaction/
    idem/
    prompts/
  udocket_ai/
  udocket_docs/
  client_sdks/
    python/
    typescript/
```

### D. Experience & communications {#d-experience-communications}

Experience modules track staff and client UIs, assistants, communications pipelines, and
localization evidence so every touchpoint is localized and auditable.

```tree
apps/
  web/
    staff/
    client/
    shared_components/
  assistants/
communications/
  outbox/
  providers/
  templates/
localization/
  packs/
  evidence/
```

### E. Data, trust & compliance {#e-data-trust-compliance}

Data services bundle reference management, signing, search, artifact storage, and policy
residency to keep attestations and licensing consistent.

```tree
data-services/
  reference-manager/
  digital-signer/
  audit-ledger/
  search-index/
  artifact-store/
  policy-residency/
compliance/
  waivers/
  licensing/
```

### F. Infrastructure & operations {#f-infrastructure-operations}

Infrastructure directories surface Kubernetes manifests, service mesh policy, Terraform,
observability assets, runbooks, and security automation.

```tree
infra/
  kubernetes/
  service-mesh/
  terraform/
  observability/
  pipelines/
ops/
  runbooks/
  watchdogs/
  localization/
  security/
```

### G. Testing & quality {#g-testing-quality}

Testing assets cover unit, integration, contract, end-to-end, load, and localization
suites plus shared fixtures.

```tree
tests/
  unit/
  integration/
  contract/
  e2e/
  load/
  localization/
tools/
  pytest_plugins/
  fixtures/
```

### H. Documentation system {#h-documentation-system}

Documentation follows the same taxonomy as the platform, with appendices mirroring the
tree definitions and tooling living in `packages/udocket_docs`.

```tree
docs/
  index.md
  overview/
    tdd/
      appendices/
        repository_trees.md
  platform/
  automation/
  data/
  experience/
  customer/
  ops/
  architecture/
  typing/
```
