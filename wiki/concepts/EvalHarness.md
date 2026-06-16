---
tags: [concept]
updated: 2026-06-08
---

# Eval Harness

Automated evaluation framework for [[Nexus]], owned by [[PriyaNair]].

## Status (as of June 2, 2026)
- Scaffold complete.
- Being wired to GitHub Actions CI during June 2–13 sprint ([[2026-06-02-sprint-planning]]).

## Metrics (first three, to be defined this sprint)
1. **Extraction accuracy** — correctness of extracted content.
2. **Entity recall** — completeness of entity identification.
3. **Hallucination rate** — frequency of fabricated information.

## CI Policy
Eval runs on **every PR**, not nightly. Decision made at [[2026-06-02-sprint-planning]] — nightly was deemed too slow given team velocity. Adds ~4 min to CI pipeline.