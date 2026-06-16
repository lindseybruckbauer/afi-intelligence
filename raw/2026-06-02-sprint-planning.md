# Sprint Planning — June 2, 2026

**Attendees:** Maya Chen (lead), Darius Okafor, Priya Nair, Tom Escalante  
**Facilitator:** Maya  
**Duration:** 60 min

---

## Sprint Goal

Ship the document ingestion pipeline end-to-end by June 13. This means a user can drop a PDF or markdown file into the intake folder, the agent processes it, and the result is queryable via the internal API.

---

## What we carried over from last sprint

- Darius: PDF extraction worker still flaky on scanned docs — punted to this sprint, now P0
- Priya: eval harness scaffold is done but not wired to CI yet
- Tom: API rate limiting middleware — Done, merged Friday

---

## This sprint

**Darius**
- Fix PDF OCR fallback (use Tesseract when pypdf fails on scanned pages)
- Write unit tests for the extraction worker
- ETA: June 6 for the fix, June 9 for tests

**Priya**
- Wire eval harness to GitHub Actions
- Define first 3 eval metrics: extraction accuracy, entity recall, hallucination rate
- Pair with Maya on prompt tuning Thursday

**Tom**
- Build the intake folder watcher (inotify-based, Python)
- Connect watcher to the ingestion queue (Redis)
- Document the queue schema

**Maya**
- Finalize the agent prompt for ingestion
- Review Darius's OCR fix
- Unblock Priya on eval metric definitions by EOD Tuesday

---

## Decisions made

1. **Tesseract over AWS Textract for OCR** — cost reason. Textract is $1.50/1000 pages, Tesseract is free. Quality difference acceptable for internal docs. Revisit if we onboard external clients. (Owner: Darius)

2. **Redis for the ingestion queue, not RabbitMQ** — team already has Redis running for the rate limiter. Adding RabbitMQ is infra overhead we don't need right now. (Owner: Tom)

3. **Eval runs on every PR, not nightly** — Priya pushed for this. Nightly catches regressions too late given our velocity. Adds ~4 min to CI. Accepted. (Owner: Priya)

---

## Blockers

- Darius needs access to the shared S3 bucket for test PDFs. Maya to request by EOD today.
- No blockers for Priya or Tom.

---

## Next sync

June 5, Thursday standup — Darius demo of OCR fix if ready.
