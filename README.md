# SQLCon EU 2026 keynote demos

One repository for the keynote, built around the pillar **any database, one data estate**.
Each demo closes a chapter, and demo 3 ties the first two together.

| Demo | Title | Slide title | Owner |
|---|---|---|---|
| 1 | Sovereign Private Cloud with SQL Server | Your data and AI, on infrastructure you control | [demo1-azure-local](demo1-azure-local) |
| 2 | Mission-Critical, at Any Scale | Start small. Scale without re-architecting. | [demo2-mission-critical](demo2-mission-critical) |
| 3 | Your Data Estate Running Itself | From estate-wide signal to application fix | [demo3-estate-running-itself](demo3-estate-running-itself) |

The [SSMS what's new demo](ssms-whatsnew) shows the recorded two-minute workflow from poorly formatted coworker SQL to a performance recommendation in GitHub Copilot Agent Mode.

The [Caldova Hands-Free Indexing demo](corenote/handsfreeindexing) follows one
unchanged dashboard query through the Azure SQL index lifecycle. Automatic tuning
creates a covering index from workload evidence, controlled insert/delete activity
makes it sparse, and Automatic Index Compaction repacks eligible leaf pages. The
demo pairs live query duration and logical reads with persisted physical index
telemetry; it does not use synthetic delays, query hints, or a manual index fallback.

## Why one repository

Demos 2 and 3 share an application. In demo 2 it is an evidence search app on Azure SQL
Hyperscale. In demo 3 the same product, in a different view, is the slow application that
Database Hub surfaces. Keeping both here means the two apps look like one product on stage
instead of two unrelated samples.

Shared visual language lives in [shared/design-system](shared/design-system). Anything that
needs to look like the keynote app should import those tokens rather than restyle from scratch.

## Layout

```
corenote/
  handsfreeindexing/          Azure SQL automatic indexing and index compaction
    app/                      Live operations dashboard backed by Azure SQL
    deploy/                   Infrastructure, workload, lifecycle, and cleanup scripts
    DEMO-RUNBOOK.md           Lifecycle gates and presentation guidance
demo1-azure-local/            SQL Server 2025 with Foundry Local on Azure Local
  app/                        ASP.NET Core transfer-center application
  database/                   Ordered deployment and validation scripts
  setup/                      Azure Local gateway setup and verification
  hyperscale-foundry/         Optional Azure SQL + Microsoft Foundry variant
demo2-mission-critical/     Vector search on Hyperscale, serverless economics
  app/                      React client + Express API (Caldova)
  database/                 Approval-gated T-SQL and deployment scripts
  workload/                 Scheduled job that exercises auto-pause and resume
  staging/                  Deterministic source and embedding packages
  recording/                Frame capture and video assembly
  docs/                     Demo plan, stage script, recording script
demo3-estate-running-itself/
  app/                      Operations view sharing the demo 2 design system
  database/                 Invoice schema, seed, and the anti-pattern queries
  docs/                     What to show, and what the fix actually changes
ssms-whatsnew/
  setup/                    Public environment setup and rehearsal guidance
  demo/                     Recorded storyboard and alternate demo concept
  assets/                   Setup, query, validation, and teardown SQL
shared/
  design-system/            Tokens and layout primitives used by both apps
  SKILL.md                  Agent skill for building a matching demo app
```

## Ground rules carried over from demo 2

These are not stylistic preferences. They are what keeps the demo honest on stage.

- No latency or scale number is spoken unless it appears in a retained report.
- The app refuses to run a live query when its data contract does not verify, and it
  shows blank timings rather than a number it cannot back up.
- `FORCE_ANN_ONLY` stays in the vector query so a silent fallback to a full scan is
  impossible.
- The large benchmark database is read-only for this work. No index is created on it
  until its embeddings finish loading.
- `research-replica` is a serverless named replica of that database. It shares the
  primary's storage, so it inherits the vector index the moment the team builds it.

## Getting started

Each demo folder has its own README with prerequisites and run steps. Start there.
