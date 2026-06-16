---
tags: [entity]
updated: 2026-06-08
---

# Tom Escalante

**Role:** Infrastructure engineer on [[Nexus]]
**Responsibilities:** Queue, API, intake watcher, rate limiting.

## Sprint — June 2–13, 2026
Per [[2026-06-02-sprint-planning]]:
- Build intake folder watcher (inotify-based, Python).
- Connect watcher to the ingestion queue ([[Redis]]).
- Document the queue schema.
- Owner of the decision to use [[Redis]] over RabbitMQ for the ingestion queue.

## Previous Sprint
- API rate limiting middleware — **Done**, merged Friday before sprint.