---
name: run-handsfree-indexing
description: "Prepare, deploy, validate, rehearse, monitor, or clean up the SQLCon EU 2026 Caldova Hands-Free Indexing demo. Use for Azure SQL automatic indexing, Automatic Index Compaction, the Hyperscale dashboard workload, index bloat, compaction progress, or the demo's Azure deployment scripts."
argument-hint: "Mode: prepare, deploy, preflight, rehearse, status, or cleanup"
---

# Run Hands-Free Indexing

Guide the user through the existing Azure SQL Database Hyperscale demo. Treat
the [package README](../../../corenote/handsfreeindexing/README.md) and
[demo runbook](../../../corenote/handsfreeindexing/DEMO-RUNBOOK.md) as the
sources of truth. Run only the wrappers in `deploy`; do not reproduce their
Azure CLI or SQL logic manually.

## Invariants

- Use the unchanged `demo.usp_PatientAccessDashboard` procedure.
- The qualifying nonclustered index must be created by Azure SQL and report
  `auto_created = 1`.
- Never create a manual fallback index, force a plan, add a query hint, or drop
  and recreate the automatic index.
- Bloat and compaction eligibility must use the existing bounded insert/delete
  workloads. Never update surviving rows.
- Pair `DETAILED` physical statistics with the latest real dashboard duration
  and logical reads. Never invent or interpolate measurements.

## Safety Rules

- Confirm the Azure account, tenant, subscription, resource group, SQL region,
  App Service region, and vCore count before deployment.
- Explain that deployment creates billable Azure SQL Hyperscale, App Service,
  networking, private endpoint, and DNS resources. Require explicit user
  approval immediately before `01-deploy-infrastructure.ps1`.
- Require explicit approval before database initialization, bloat creation,
  enabling compaction, and cleanup.
- `99-remove.ps1` deletes the entire configured resource group. Show the exact
  resource group and require confirmation before running it; do not suppress
  its PowerShell confirmation.
- Do not request credentials in chat. Authentication must use Azure CLI,
  Microsoft Entra, and managed identity as implemented by the scripts.
- Do not print access tokens or broaden the exact-IP bootstrap firewall rule.

## Select a Mode

- `prepare`: validate tools, identity, configuration, and feature availability.
- `deploy`: run the four documented deployment steps with approval gates.
- `preflight`: verify an existing environment without changing it.
- `rehearse`: guide the measured indexing lifecycle one phase at a time.
- `status`: capture the current documented state once; do not poll continuously.
- `cleanup`: remove the dedicated resource group after explicit confirmation.

## Prepare

1. Read `deploy\00-config.ps1`; do not run it directly.
2. Require PowerShell 7, Azure CLI, go-sqlcmd, and the .NET 10 SDK.
3. Require `AZURE_SUBSCRIPTION_ID`. Accept only the documented optional
   `CALDOVA_*` environment overrides.
4. Use read-only account checks to confirm the active identity and that the
   configured subscription matches `AZURE_SUBSCRIPTION_ID`.
5. Confirm the selected SQL region supports the Automatic Index Compaction
   preview. If this cannot be verified, stop and mark the gate `NOT VERIFIED`.
6. Summarize the resolved resource names and locations without exposing tokens.

## Deploy

From `corenote\handsfreeindexing`, run one step at a time and require success
before continuing:

1. After billable-resource approval:

   ```powershell
   .\deploy\01-deploy-infrastructure.ps1
   ```

2. After confirmation that recreating the isolated demo schema and loading two
   million rows is intended:

   ```powershell
   .\deploy\02-initialize-database.ps1
   ```

3. Publish the application:

   ```powershell
   .\deploy\03-publish-app.ps1
   ```

4. Verify the deployed environment:

   ```powershell
   .\deploy\04-verify.ps1
   ```

Require an online Hyperscale database, Entra-only authentication, an approved
private endpoint, a running Windows App Service, `/healthz = ok`, and
`/readyz = ready`.

## Preflight

Run `04-verify.ps1` and report each documented gate. Confirm the presenter can
open the Operations Dashboard and Index Health views. Do not initialize data,
run workload, create bloat, or enable compaction during preflight.

## Rehearse

Guide one phase at a time and wait for the user between phases:

1. **No Nonclustered Index**: initialize only if a fresh environment is
   explicitly intended; refresh the dashboard and confirm `Missing Index`.
2. **Automatic Tuning**: run one 15-minute interval with
   `05-run-workload.ps1`, then run `06-show-index-recommendation.ps1` and
   `07-check-auto-index.ps1`. If the index is not ready, stop and tell the user
   to repeat later. Never loop unattended.
3. **Create Real Bloat**: only after `auto_created = 1` is proven and the user
   approves, run `08-create-bloat.ps1`. Refresh the dashboard, then run
   `10-check-progress.ps1` once.
4. **Automatic Index Compaction**: after approval, run
   `09-enable-compaction.ps1`. On user request, refresh the dashboard and run
   `10-check-progress.ps1` once per observation.
5. Complete only when measured telemetry shows materially fewer pages, higher
   density, and recovered query performance. Preserve the runbook's final
   presentation message.

Automatic tuning and compaction are asynchronous. Do not claim completion from
elapsed time alone and do not use sleep loops or continuous polling.

## Status

Run `10-check-progress.ps1` once and summarize phase, index name,
`auto_created`, page count, density, logical reads, query duration, and AIC
state from the output. If no paired measurement exists, say so.

## Cleanup

Show the resolved resource group, explain that every contained resource will be
deleted, obtain explicit confirmation, and then run:

```powershell
.\deploy\99-remove.ps1
```

Report that deletion was started; do not claim completion until Azure confirms
the resource group no longer exists.

## Completion Report

Report mode, subscription name, resource group, commands run, gates passed,
current lifecycle phase, and remaining asynchronous or manual work. Do not
include tokens or credentials.