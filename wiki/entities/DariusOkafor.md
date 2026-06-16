---
tags: [entity]
updated: 2026-06-08
---

# Darius Okafor

**Role:** Backend engineer on [[Nexus]]
**Responsibilities:** Extraction worker, OCR pipeline, PDF handling.

## Sprint — June 2–13, 2026
Per [[2026-06-02-sprint-planning]]:
- **P0:** Fix PDF OCR fallback — use [[Tesseract]] when pypdf fails on scanned pages (ETA June 6).
- Write unit tests for the extraction worker (ETA June 9).
- Owner of the decision to use [[Tesseract]] over AWS Textract for OCR.
- **Blocker:** Needs access to shared S3 bucket for test PDFs (Maya to request).

## Previous Sprint
- PDF extraction worker was flaky on scanned docs — carried over.