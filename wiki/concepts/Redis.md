---
tags: [concept]
updated: 2026-06-08
---

# Redis

In-memory data store used in [[Nexus]] for:
1. **Message / ingestion queue** — the intake watcher publishes jobs to Redis, consumed by the extraction worker. Owned by [[TomEscalante]].
2. **Rate limiting** — the [[FastAPI]] API rate-limiting middleware uses Redis. Middleware shipped and merged as of late May 2026.

## Decision: Redis over RabbitMQ for Ingestion Queue
Decided during [[2026-06-02-sprint-planning]]. Rationale:
- Redis was already running for the rate limiter.
- Adding RabbitMQ would introduce unnecessary infrastructure overhead for current needs.