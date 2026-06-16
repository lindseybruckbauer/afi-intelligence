---
tags: [concept]
updated: 2026-06-08
---

# Tesseract

Open-source OCR engine used as the fallback for scanned PDFs in [[Nexus]].

## Usage in Nexus
When `pypdf` fails on scanned pages, the extraction worker falls back to Tesseract. [[DariusOkafor]] owns the OCR pipeline.

## Decision: Tesseract over AWS Textract
Decided during [[2026-06-02-sprint-planning]]. Rationale:
- Textract costs $1.50 / 1,000 pages; Tesseract is free.
- Quality difference acceptable for internal documents.
- Decision to be revisited if Nexus onboards external clients.