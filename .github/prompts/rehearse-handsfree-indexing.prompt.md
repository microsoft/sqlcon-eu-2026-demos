---
name: "Rehearse Hands-Free Indexing"
description: "Guide the measured Azure SQL automatic indexing and Automatic Index Compaction demo lifecycle."
agent: "agent"
---

Use the [Run Hands-Free Indexing skill](../skills/run-handsfree-indexing/SKILL.md)
in `rehearse` mode. Run non-destructive preflight first, preserve every runbook
invariant, and guide one lifecycle phase at a time. Require proof that the index
has `auto_created = 1` before bloat, obtain approval before each data-changing
step, never loop asynchronous checks unattended, and report only measured
telemetry.