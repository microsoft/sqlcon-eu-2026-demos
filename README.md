# SQLCon EU 2026 keynote demos

One repository for the keynote, built around the pillar **any database, one data estate**.
Each demo closes a chapter, and demo 3 ties the first two together.

| Demo | Title | Slide title | Owner |
|---|---|---|---|
| 1 | Sovereign Private Cloud with SQL Server | Your data and AI, on infrastructure you control | [demo1-azure-local](demo1-azure-local) |
| 2 | Mission-Critical, at Any Scale | Start small. Scale without re-architecting. | [demo2-mission-critical](demo2-mission-critical) |
| 3 | Your Data Estate Running Itself | From estate-wide signal to application fix | [demo3-estate-running-itself](demo3-estate-running-itself) |

Additional corenote segments also live here. They are separate from the numbered
keynote demos:

| Segment | Format | Repository status | Start here |
|---|---|---|---|
| SSMS what's new: From Problem to Answer | Recorded; reproducible | Setup, storyboard, SQL assets, validation, teardown, and fallback guidance are present | [Demo package](corenote/ssms-whatsnew/README.md) |
| SSMS what's new: Five Customer Asks We Delivered | Alternate recorded concept | Storyboard and SQL assets are present; feature labels, exact interactions, and final recording still need validation | [Alternate storyboard](corenote/ssms-whatsnew/demo/version-2-five-customer-asks.md) |
| SSMS migration and agentic modernization | Existing 2:09 recording | Talk track and transcript are present. The source application, database, SSMS assessment setup, migration prompt, and replay instructions are not in this repository | [Recording handoff](corenote/migration/README.md) |

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
  docs/                     Stage script
demo3-estate-running-itself/
  app/                      Operations view sharing the demo 2 design system
  database/                 Invoice schema, seed, and the anti-pattern queries
  docs/                     What to show, and what the fix actually changes
shared/
  design-system/            Tokens and layout primitives used by both apps
  SKILL.md                  Agent skill for building a matching demo app
corenote/ssms-whatsnew/
  setup/                    Public environment setup and rehearsal guidance
  demo/                     Recorded storyboard and alternate demo concept
  assets/                   Setup, query, validation, and teardown SQL
corenote/migration/
  src/                      Nandiyo Logistics ASP.NET Core application
  database/                 Assessment inventory and remediation scripts
  infra/                    App Service and Azure SQL Bicep
  skills/                   SQL migration and assessment skills
  docs/                     End-to-end modernization workshop
```

Folders are organized by demo ownership. Add a new keynote demo in its own top-level
folder; keep assets, setup, and presenter notes inside that folder. Shared code belongs in
`shared/` only when at least two demos use it. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Ground rules carried over from demo 2

These are not stylistic preferences. They are what keeps the demo honest on stage.

- No latency or scale number is spoken unless it appears in a retained report.
- The app refuses to run a live query when its data contract does not verify, and it
  shows blank timings rather than a number it cannot back up.
- `FORCE_ANN_ONLY` stays in the vector query so a silent fallback to a full scan is
  impossible.
- A named replica shares the primary's storage, so it inherits the primary's vector index
  without a second index build and without copying data.

## Getting started

Each demo folder has its own README with prerequisites and run steps. Start there.

## Public release status

The repository is usable for internal rehearsal but is not ready to publish unchanged:

- Demo 3 is explicitly a starting point.
- The SSMS what's new Version 1 workflow must be validated in the final SSMS build and
  event database; fallback screenshots and recording links are still external.
- The SSMS migration segment is reproducible. `corenote/migration` ships the application,
  database, assessment and remediation scripts, infrastructure, migration skills, and an
  end-to-end workshop guide. The original recording stays outside Git.
- Demo 2 targets 1M rows. It was built against a 1B-row index, but 1M is what ships here
  so the demo stays repeatable.
- Demo recordings must remain outside Git. Publish them through an approved media location
  and link to them if needed.
- The repository owner must add the approved license and code of conduct before public
  release.

Before publishing, run the app builds, validate every stage claim against a retained
report, scan for credentials and local paths, and verify all Markdown links.
