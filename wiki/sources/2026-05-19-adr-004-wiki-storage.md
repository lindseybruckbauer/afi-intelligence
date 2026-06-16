---
tags: [source]
updated: 2026-06-08
---

# ADR-004: Wiki Storage — Markdown + Git vs Vector Database

**Date:** May 19, 2026
**Status:** Accepted
**Deciders:** [[MayaChen]], [[PriyaNair]]
**Consulted:** [[DariusOkafor]], [[TomEscalante]]

## Summary

Architecture Decision Record evaluating two storage options for the [[Nexus]] wiki: a vector database (Pinecone or Chroma) versus plain Markdown files in Git. The team chose **Markdown + Git** (Option B).

## Key factors

- At projected scale (< 500 pages for v1), LLM-navigates-the-index is sufficient for querying.
- **Human readability** was the decisive factor — [[PriyaNair]] argued that if the team can't directly read and audit the wiki, trust in the agent's output is lost.
- Git provides version history, diff, blame, and collaboration workflows for free.
- Markdown files work with [[Obsidian]] for browsing (graph view, backlinks, search) without building a custom UI.
- Vector DB (Pinecone/Chroma) offers semantic search but adds operational overhead, infra complexity, and produces opaque embeddings that can't be reviewed via git diff.
- Team has no existing expertise with Chroma or Pinecone.

## Decision

**Option B — Markdown + Git.** Revisit if wiki exceeds ~1000 pages or query latency becomes a problem; a local Chroma instance could be layered on top without changing the storage model.

## Consequences

- [[TomEscalante]] builds the query API to pass relevant wiki pages to the LLM as context (not a vector index).
- [[PriyaNair]]'s eval harness reads markdown files directly for ground truth comparison.
- All wiki content lives in the Git repo — same review workflow as code.
- [[Obsidian]] is the standard browsing interface.
- Concurrent ingest: last-write-wins for now; revisit at > 3 simultaneous contributors.

## Revisit triggers

- Wiki exceeds 1000 pages and query latency > 10s
- Team grows beyond 8 people
- External clients onboarded (semantic search becomes user-facing)