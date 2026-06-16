---
tags: [source]
updated: 2026-06-08
---

# Project Nexus — Overview (Summary)

**Source:** `raw/2026-05-28-project-nexus-overview.md`
**Date:** 2026-05-28
**Owner:** [[MayaChen]]

## Summary

Nexus is an internal document intelligence platform currently in Sprint 4 of 8. It ingests unstructured documents (PDFs, markdown, meeting transcripts, Notion exports), processes them with an LLM agent, generates structured wiki pages, and exposes content via a REST query API for other agents and internal tools.

## Motivation

The team suffers from fragmented institutional memory — 18 months of meeting notes, decision records, architecture docs, and postmortems are scattered across Google Drive, Notion, and personal notes. New team members spend 2–3 weeks getting context, and architectural decisions get re-litigated because original reasoning is hard to find. Nexus treats knowledge as a living, maintained artifact.

## Core Loop

1. Document dropped into intake folder
2. Extraction worker parses and chunks content
3. LLM agent extracts entities/concepts and writes structured wiki pages
4. Wiki pages indexed and exposed via query API
5. Other agents query API in natural language, receive cited answers

## Stack

| Layer | Technology | Notes |
|---|---|---|
| Ingestion | Python, pypdf, [[Tesseract]] | Tesseract as OCR fallback for scanned docs |
| Queue | [[Redis]] | Already in infra for rate limiting |
| LLM agent | Claude claude-opus-4-6 via Anthropic API | Prompt managed in `prompts/ingest_v2.md` |
| Wiki storage | Markdown files in Git | [[Obsidian]] for browsing (see [[2026-05-19-adr-004-wiki-storage]]) |
| Query API | [[FastAPI]] | Internal only, no auth yet |
| Eval | Custom harness, GitHub Actions CI | Metrics: extraction accuracy, entity recall, hallucination rate |

## Team Roles

- **[[MayaChen]]** — Lead. Agent prompt design, architecture decisions, stakeholder comms.
- **[[DariusOkafor]]** — Backend. Extraction worker, OCR pipeline, PDF handling.
- **[[PriyaNair]]** — ML/Eval. Eval harness, metric definitions, prompt tuning support.
- **[[TomEscalante]]** — Infrastructure. Queue, API, intake watcher, rate limiting.

## Scope (v1)

**In scope:** PDF and markdown ingestion, entity/concept extraction, wiki page generation/maintenance, query API, eval pipeline in CI.

**Out of scope:** External client access, authentication/authorization, UI, image/audio ingestion, real-time ingestion (batch only).

## Key Decisions

| Date | Decision | Rationale |
|---|---|---|
| May 12 | Claude claude-opus-4-6 over GPT-4o | Better instruction following on structured output in internal benchmarks |
| May 19 | Markdown + Git over vector DB | Simpler, no infra, human-readable, Obsidian-compatible (see [[2026-05-19-adr-004-wiki-storage]]) |
| May 26 | [[Redis]] over RabbitMQ for queue | Already in stack, sufficient for current volume |
| June 2 | [[Tesseract]] over AWS Textract for OCR | Cost — Textract $1.50/1000 pages vs Tesseract is free |

## Success Metrics (v1)

- Ingestion latency < 30s per document
- Entity recall > 85% on internal test set
- Hallucination rate < 5% on query responses
- New team member onboarding time reduced from ~3 weeks to < 1 week