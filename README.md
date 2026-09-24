# SQLCon EU 2026 demos

Demo applications, deployment assets, and presenter guidance for SQLCon EU 2026,
built around the theme **any database, one data estate**.

## Keynote demos

| Demo | Story | Start here |
|---|---|---|
| 1. Sovereign Private Cloud with SQL Server | Run data and AI on organization-controlled infrastructure with SQL Server 2025, Azure Local, and Foundry Local. | [Demo 1](demo1-azure-local) |
| 2. Mission-Critical, at Any Scale | Combine vector search, Azure SQL Database Hyperscale, and serverless named replicas in the Caldova evidence-search application. | [Demo 2](demo2-mission-critical) |
| 3. Your Data Estate Running Itself | Use estate-wide signals to find a slow application and carry the investigation through to a concrete fix. | [Demo 3](demo3-estate-running-itself) |

Demos 2 and 3 share the Caldova application and visual language so the keynote
moves from application scale to estate operations as one continuous story.

## Corenote demos

The [corenote collection](corenote) includes:

- [Caldova Evidence Agent](corenote/caldovaevidenceagent): grounded biomedical
  research using Azure SQL, SQL MCP Server, Microsoft Foundry, and Teams.
- [Caldova Hands-Free Indexing](corenote/handsfreeindexing): automatic indexing
  and Automatic Index Compaction on Azure SQL Database Hyperscale.
- [Nandiyo Logistics migration lab](corenote/migration): an end-to-end SQL Server
  and ASP.NET Core migration to Azure SQL Database and Azure App Service.
- [SSMS what's new](corenote/ssms-whatsnew): reproducible feature demonstrations,
  storyboards, SQL assets, and presenter guidance.

## Repository structure

| Path | Contents |
|---|---|
| [demo1-azure-local](demo1-azure-local) | Keynote Demo 1 application, database, setup, and cloud variant |
| [demo2-mission-critical](demo2-mission-critical) | Keynote Demo 2 application, data pipeline, workload, and scripts |
| [demo3-estate-running-itself](demo3-estate-running-itself) | Keynote Demo 3 application, database, and presenter guidance |
| [corenote](corenote) | Corenote demo packages and workshops |
| [shared](shared) | Shared design system and reusable guidance |

## Run with GitHub Copilot

Open this repository in VS Code with GitHub Copilot Chat, select **Agent** mode,
and type `/` to run one of the workspace prompts:

| Prompt | Purpose |
|---|---|
| `/prepare-keynote-demo-1` | Prepare and validate Caldova Regional Care on Azure Local |
| `/rehearse-keynote-demo-1` | Walk through the locked Keynote Demo 1 presenter flow |
| `/prepare-handsfree-indexing` | Prepare, deploy, and verify the Hands-Free Indexing environment |
| `/rehearse-handsfree-indexing` | Walk through automatic indexing and compaction one measured phase at a time |

The Caldova Evidence Agent also includes natural-language skills that Copilot
selects from your request:

| Ask Copilot to | Skill |
|---|---|
| Build, deploy, repair, or verify the Caldova Evidence Agent | [Build Caldova Evidence Agent](.github/skills/build-caldova-evidence-agent/SKILL.md) |
| Start, open, check, or stop the Caldova Evidence Agent application | [Run Caldova Evidence Agent](.github/skills/run-caldova-evidence-agent/SKILL.md) |
| Rehearse or guide the Caldova Evidence Agent demo one beat at a time | [Demo Caldova Evidence Agent](.github/skills/demo-caldova-evidence-agent/SKILL.md) |

The prompts use repository skills in [.github/skills](.github/skills). They read
the current runbooks, use the checked-in scripts, protect credentials, and stop
for confirmation before elevated, billable, data-changing, or destructive work.

## Getting started

Open the README in the demo folder you want to run. Each demo documents its own
prerequisites, deployment steps, validation, and cleanup.

See [CONTRIBUTING.md](CONTRIBUTING.md) before changing shared assets or adding a
new demo.
