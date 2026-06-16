# Project Nexus — Overview

**Last updated:** May 28, 2026  
**Owner:** Maya Chen  
**Status:** Active — Sprint 4 of 8

---

## What we're building

Nexus is an internal document intelligence platform. It ingests unstructured documents (PDFs, markdown, meeting transcripts, Notion exports) and makes their content queryable by other agents and internal tools via a REST API.

The core loop:
1. Document dropped into intake folder
2. Extraction worker parses and chunks the content
3. LLM agent processes chunks, extracts entities and concepts, writes structured wiki pages
4. Wiki pages indexed and exposed via query API
5. Other agents query the API in natural language and get cited answers

---

## Why we're building it

The team's biggest friction point is institutional memory. We have 18 months of meeting notes, decision records, architecture docs, and project postmortems scattered across Google Drive, Notion, and personal notes. Every new team member spends 2-3 weeks just getting context. Every architectural decision gets re-litigated because nobody can find the original reasoning.

Nexus solves this by treating knowledge as a living, maintained artifact rather than a static document dump.

---

## Stack

| Layer | Technology | Notes |
|---|---|---|
| Ingestion | Python, pypdf, Tesseract | Tesseract as OCR fallback for scanned docs |
| Queue | Redis | Already in infra for rate limiting |
| LLM agent | Claude claude-opus-4-6 via Anthropic API | Prompt managed in `prompts/ingest_v2.md` |
| Wiki storage | Markdown files in Git | Obsidian for browsing |
| Query API | FastAPI | Internal only, no auth yet |
| Eval | Custom harness, GitHub Actions CI | Metrics: extraction accuracy, entity recall, hallucination rate |

---

## Team

- **Maya Chen** — Lead. Owns agent prompt design, architecture decisions, stakeholder comms.
- **Darius Okafor** — Backend. Owns extraction worker, OCR pipeline, PDF handling.
- **Priya Nair** — ML/Eval. Owns eval harness, metric definitions, prompt tuning support.
- **Tom Escalante** — Infrastructure. Owns queue, API, intake watcher, rate limiting.

---

## What's in scope (v1)

- PDF and markdown ingestion
- Entity and concept extraction
- Wiki page generation and maintenance
- Query API (natural language in, cited answer out)
- Eval pipeline in CI

## What's out of scope (v1)

- External client access
- Authentication / authorization on the API
- UI (API only)
- Image and audio ingestion
- Real-time ingestion (batch only for now)

---

## Key decisions log

| Date | Decision | Rationale |
|---|---|---|
| May 12 | Claude claude-opus-4-6 over GPT-4o for the agent | Better instruction following on structured output tasks in internal benchmarks |
| May 19 | Markdown + Git over a vector DB for wiki storage | Simpler, no infra, human-readable, works with Obsidian |
| May 26 | Redis over RabbitMQ for queue | Already in stack, sufficient for current volume |
| June 2 | Tesseract over AWS Textract for OCR | Cost — Textract $1.50/1000 pages vs free |

---

## Success metrics for v1

- Ingestion latency < 30s per document
- Entity recall > 85% on internal test set
- Hallucination rate < 5% on query responses
- New team member onboarding time reduced from ~3 weeks to < 1 week
