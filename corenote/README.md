# SQLCon EU 2026 corenote demos

This folder contains three end-to-end demos for the SQLCon EU 2026 corenote.
Each demo has its own prerequisites, deployment guidance, and cleanup steps.

## Caldova Evidence Agent

[Caldova Evidence Agent](caldovaevidenceagent) turns a biomedical search
experience into a conversational, grounded research agent. Azure SQL performs
deterministic vector retrieval, Data API builder exposes approved stored
procedures through SQL MCP Server, and a Microsoft Foundry agent plans and
synthesizes a multi-source investigation for delivery in Microsoft Teams.

The design keeps SQL access read-only and governed, uses managed identities,
and requires material claims to be traceable to cited corpus evidence.

## Caldova Hands-Free Indexing

[Caldova Hands-Free Indexing](handsfreeindexing) demonstrates the lifecycle of
one unchanged dashboard query on Azure SQL Database Hyperscale. Automatic
tuning creates a useful index from workload evidence, controlled activity
leaves it sparse, and Automatic Index Compaction repacks eligible leaf pages.

The live dashboard pairs query duration and logical reads with persisted
physical index telemetry without query hints, synthetic delays, or a manual
index fallback.

## Nandiyo Logistics migration lab

[Nandiyo Logistics migration lab](migration) shows how to assess and replatform
a fictional ASP.NET Core and SQL Server application to Linux Azure App Service
and Azure SQL Database Hyperscale.

The guided workshop covers assessment, focused remediation, infrastructure
deployment, offline BACPAC migration, Microsoft Entra-only authentication,
managed identity, workflow validation, and cleanup.

## Run Hands-Free Indexing with GitHub Copilot

Open the repository in VS Code with GitHub Copilot Chat in **Agent** mode, type
`/`, and choose:

- `/prepare-handsfree-indexing` to validate configuration, deploy with approval
	gates, and verify the Azure environment.
- `/rehearse-handsfree-indexing` to guide the measured automatic-indexing and
	Automatic Index Compaction lifecycle one phase at a time.

Both prompts use the
[Run Hands-Free Indexing skill](../.github/skills/run-handsfree-indexing/SKILL.md),
which preserves the runbook invariants and requires confirmation before
billable, data-changing, or destructive actions.

## Getting started

Choose a demo above and follow its README. These demos can create billable Azure
resources, so review the prerequisites and cleanup guidance before deployment.
## Corenote segment index

| Segment | Materials |
| --- | --- |
| SSMS What's New | [Setup, storyboards, SQL assets, and presenter guidance](ssms-whatsnew/README.md) |
| One Connection String to Rule Them All | [Drivers segment](drivers/README.md) |
| SSMS migration and agentic modernization | [Nandiyo Logistics migration lab](migration/README.md) |
