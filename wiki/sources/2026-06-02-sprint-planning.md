---
tags: [source]
updated: 2026-06-08
---

# Sprint Planning — June 2, 2026

**Source:** `raw/2026-06-02-sprint-planning.md`
**Attendees:** [[MayaChen]], [[DariusOkafor]], [[PriyaNair]], [[TomEscalante]]
**Facilitator:** [[MayaChen]]

## Sprint Goal
Ship the document ingestion pipeline end-to-end by June 13. A user should be able to drop a PDF or Markdown file into the intake folder, have the agent process it, and query the result via the internal API.

## Carry-overs from Previous Sprint
- [[DariusOkafor]]: PDF extraction worker still flaky on scanned docs — now P0.
- [[PriyaNair]]: Eval harness scaffold done but not yet wired to CI.
- [[TomEscalante]]: API rate limiting middleware — **Done**, merged Friday.

## Sprint Commitments

| Person | Tasks | ETA |
|---|---|---|
| [[DariusOkafor]] | Fix PDF OCR fallback (use [[Tesseract]] when pypdf fails on scanned pages); write unit tests for extraction worker | Fix June 6, tests June 9 |
| [[PriyaNair]] | Wire eval harness to GitHub Actions; define first 3 eval metrics (extraction accuracy, entity recall, hallucination rate); pair with Maya on prompt tuning Thursday | Sprint end |
| [[TomEscalante]] | Build intake folder watcher (inotify-based, Python); connect watcher to ingestion queue ([[Redis]]); document queue schema | Sprint end |
| [[MayaChen]] | Finalize agent prompt for ingestion; review Darius's OCR fix; unblock Priya on eval metric definitions by EOD Tue June 3 | Sprint end |

## Decisions

1. **[[Tesseract]] over AWS Textract for OCR** — Cost reason. Textract is $1.50/1000 pages; Tesseract is free. Quality difference acceptable for internal docs. Revisit if external clients are onboarded. Owner: [[DariusOkafor]].
2. **[[Redis]] for ingestion queue, not RabbitMQ** — Team already runs Redis for the rate limiter; adding RabbitMQ is unnecessary infra overhead for now. Owner: [[TomEscalante]].
3. **Eval runs on every PR, not nightly** — [[PriyaNair]] pushed for this; nightly catches regressions too late at current velocity. Adds ~4 min to CI. Accepted. Owner: [[PriyaNair]].

## Blockers
- [[DariusOkafor]] needs access to the shared S3 bucket for test PDFs. [[MayaChen]] to request by EOD June 2.

## Next Sync
June 5 Thursday standup — Darius demo of OCR fix if ready.