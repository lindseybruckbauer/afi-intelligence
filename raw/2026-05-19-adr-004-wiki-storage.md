# ADR-004: Wiki Storage — Markdown + Git vs Vector Database

**Date:** May 19, 2026  
**Status:** Accepted  
**Deciders:** Maya Chen, Priya Nair  
**Consulted:** Darius Okafor, Tom Escalante

---

## Context

We need a storage layer for the wiki that Nexus generates. Two serious options were on the table: a vector database (Pinecone or Chroma) and plain markdown files stored in a Git repo. This decision affects how we index, query, maintain, and collaborate on the wiki.

The decision had to be made before Tom started building the query API, since the storage layer determines the query approach.

---

## Options considered

### Option A: Vector database (Pinecone or Chroma)

Store wiki content as vector embeddings. Query via semantic similarity search.

**Pros:**
- Semantic search out of the box — "find pages about OCR" works even if the word "OCR" isn't in the page
- Fast retrieval at scale (thousands of pages)
- Industry-standard approach for RAG systems
- Chroma runs locally (no SaaS dependency)

**Cons:**
- Embeddings are not human-readable — you can't browse the knowledge base without a UI
- Requires embedding pipeline to stay in sync with content — operational overhead
- Harder to review and audit what the LLM wrote
- Git diff on embeddings is meaningless — you lose version history of the actual content
- Team has no existing expertise with Chroma or Pinecone
- Adds infra complexity we don't need at current scale

### Option B: Markdown files in Git

Store wiki as plain `.md` files in a Git repository. Query by having the LLM read the index file and relevant pages.

**Pros:**
- Human-readable — anyone can browse, edit, and review the wiki directly
- Git gives version history, blame, branching, and collaboration for free
- Works with Obsidian — graph view, backlinks, search, all available without building a UI
- Zero infra — no service to run, no sync to maintain
- LLM reads the index first, then drills into relevant pages — works well at moderate scale
- Easy to audit: git diff shows exactly what the LLM changed

**Cons:**
- No semantic search — relies on the LLM reading the index and navigating by wikilinks
- Slower at large scale (100s of pages + LLM reading multiple files per query)
- Concurrent writes need coordination (two people ingesting at once can cause merge conflicts)

---

## Decision

**Option B — Markdown + Git.**

At our current and projected scale (< 500 pages for v1), the LLM-navigates-the-index approach is sufficient and the operational simplicity wins. Priya's point was decisive: if the team can't read and audit the wiki directly, we lose trust in what the agent is producing. Human readability is not optional for an internal knowledge tool.

We revisit if query latency becomes a problem or the wiki exceeds ~1000 pages. At that point, adding a local Chroma instance as a search layer on top of the markdown files is straightforward without changing the storage model.

---

## Consequences

- Tom builds the query API to pass relevant wiki pages to the LLM as context, not to query a vector index
- Priya's eval harness reads markdown files directly for ground truth comparison
- All wiki content is in the Git repo — same review workflow as code
- Obsidian is the standard browsing interface — team should install it
- Concurrent ingest conflict resolution: last write wins for now, revisit at > 3 simultaneous contributors

---

## Revisit trigger

If any of the following occur, reopen this decision:
- Wiki exceeds 1000 pages and query latency > 10s
- Team grows beyond 8 people (concurrent write conflicts become frequent)
- We onboard external clients (semantic search becomes a user-facing requirement)
