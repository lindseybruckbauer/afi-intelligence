---
tags: [entity]
updated: 2026-06-08
---

# Nexus

**Type:** Internal document intelligence platform and wiki-generating agent.

## Current Sprint Goal (June 2–13, 2026)
Ship the document ingestion pipeline end-to-end: a user drops a PDF or Markdown file into the intake folder → agent processes it → result is queryable via the internal API. See [[2026-06-02-sprint-planning]].

## Key Architecture Decisions
- Wiki storage: Markdown + Git over vector database ([[2026-05-19-adr-004-wiki-storage]]).
- OCR: [[Tesseract]] over AWS Textract — cost-driven; revisit if external clients onboarded ([[2026-06-02-sprint-planning]]).
- Ingestion queue: [[Redis]] (not RabbitMQ) — already in use for rate limiter ([[2026-06-02-sprint-planning]]).
- CI eval: Runs on every PR, not nightly ([[2026-06-02-sprint-planning]]).

## Stack
- [[FastAPI]] — query API
- [[Redis]] — message queue & rate limiting
- [[Tesseract]] — OCR fallback for scanned PDFs
- [[Obsidian]] — wiki browsing interface

## Team
- [[MayaChen]] — Lead
- [[DariusOkafor]] — Backend
- [[PriyaNair]] — ML/Eval
- [[TomEscalante]] — Infrastructure