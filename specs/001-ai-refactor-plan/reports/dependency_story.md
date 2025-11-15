# Dependency Story – Modernization Backlog

1. `analyze.atoms_extract` depends on input discovery ingest stability; once deterministic token histograms land, the stage unlocks context builder improvements.
2. `analyze.context_builder` consumes the atoms output and must validate residency tags before gaps extraction can restart. Until this stage finishes, the entire readiness gap automation chain is blocked.
3. `analyze.gaps_extract` sits on the critical path: it cannot progress without context builder data, and downstream stages (flags, release gate) all require its outputs. The backlog entry therefore carries `critical_path=true` and the highest effort range.
4. `analyze.flags_extract` follows gaps to capture governance flags; although not as costly, it inherits dependencies transitively because risk logs must align with auto-generated gaps.
5. `compose.release_gate` is the final blocking task before activation— it depends on flags extraction to ensure residency attestations reference the latest readiness hash. Release gate remains critical path because any delay here stalls external deliverables despite work finishing upstream.

Effort estimates grow cumulatively along this chain, and QA gates referenced in the backlog ensure each dependency provides concrete evidence (hash checks, logs) before the next stage starts.
