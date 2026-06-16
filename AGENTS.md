# Team Wiki — Schema

## Purpose
This is the org knowledge base. Raw sources live in `raw/`. 
The wiki lives in `wiki/`. The LLM writes and maintains all wiki files.
Humans add raw sources and ask questions. Never modify files in `raw/`.

## Naming conventions
- Entity pages: `wiki/entities/PersonName.md`, `wiki/entities/ProjectName.md`
- Concept pages: `wiki/concepts/TopicName.md`
- Source summaries: `wiki/sources/YYYY-MM-DD-title.md`

## Every page must have frontmatter:
---
tags: [entity|concept|source]
updated: YYYY-MM-DD
---

## index.md
Keep current. One line per page: [[PageName]] — one-sentence summary.

## log.md
Append-only. Every ingest: ## [YYYY-MM-DD] ingest | SourceTitle
Every saved query: ## [YYYY-MM-DD] query | Question

## Ingest workflow
1. Read the file in raw/
2. Write a summary page in wiki/sources/
3. Update or create entity/concept pages it touches
4. Update wiki/index.md
5. Append to wiki/log.md
6. Note contradictions with existing pages inline

## Query workflow
Answer from wiki pages first. Cite with [[wikilinks]].
If the answer is valuable, file it back as a new wiki page.
