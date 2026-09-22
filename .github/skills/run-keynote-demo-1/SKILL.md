---
name: run-keynote-demo-1
description: "Prepare, validate, rehearse, or troubleshoot SQLCon EU 2026 Keynote Demo 1, Caldova Regional Care on Azure Local. Use when running the Demo 1 setup, checking SQL Server 2025 and Foundry Local, validating the Azure Local gateway, starting the transfer-center app, or guiding the locked presenter flow."
argument-hint: "Mode: prepare, preflight, rehearse, or troubleshoot"
---

# Run Keynote Demo 1

Guide the user through the existing Caldova Regional Care demo. Treat the
[package README](../../../demo1-azure-local/README.md) and
[demo runbook](../../../demo1-azure-local/DEMO-RUNBOOK.md) as the sources of
truth. Use repository scripts as written; do not recreate their logic with
ad hoc commands.

## Safety Rules

- Never display or read into chat the kubeconfig, Kubernetes API key, database
  scoped credential secret, database master-key password, or a literal key from
  `chatLanguageModels.json`.
- Never retrieve a Kubernetes Secret directly for inspection. Only the existing
  setup and database wrappers may consume it.
- Do not provision, restart, scale, or modify Azure Local, AKS Arc, Foundry
  Local, the model deployment, or portal resources.
- Do not bypass TLS validation or add `--insecure`.
- Ask for explicit confirmation before running an elevated setup, restarting
  SQL Server, initializing the database, invoking the live model, or generating
  a live receiving briefing.
- Never request a secret through chat. If a terminal prompts for one, tell the
  user to enter it directly in the terminal.

## Select a Mode

Infer the mode from the request. If it is unclear, ask the user to choose:

- `prepare`: configure a demo VM and database using existing infrastructure.
- `preflight`: perform non-destructive readiness checks before presenting.
- `rehearse`: guide the locked presentation sequence one beat at a time.
- `troubleshoot`: diagnose one failed gate without broad environment changes.

## Prepare

1. Confirm the user is on the intended Windows demo VM and read
   [setup guidance](../../../demo1-azure-local/setup/README.md).
2. Check, without printing sensitive contents:
   - PowerShell is elevated before setup.
   - `C:\setup\SJ-SQLAI-admin.kubeconfig` exists, or record the alternate path.
   - SQL Server 2025 is running.
   - `az`, `kubectl`, `kubelogin`, `curl.exe`, `sqlcmd`, and the .NET 10 SDK are
     available.
3. Explain that setup imports a root certificate and restarts SQL Server. After
   explicit confirmation, run from an elevated PowerShell terminal:

   ```powershell
   Set-Location C:\setup
   Set-ExecutionPolicy -Scope Process RemoteSigned
   .\Setup.ps1
   ```

   Pass documented overrides only when the user supplied them.
4. Require exit code 0 and `Setup completed successfully.`
5. Ask before invoking the live model. If approved, run `C:\setup\test.ps1` and
   require trusted HTTPS plus HTTP 200 through SQL Server. A successful direct
   `curl` call is not sufficient.
6. From `demo1-azure-local`, determine whether `CaldovaRegionalCare` already
   exists. Use `-InitializeDatabase` only for an absent database and only after
   explicit confirmation:

   ```powershell
   .\database\Setup-CaldovaDatabase.ps1 -InitializeDatabase
   ```

   For an existing database, run the repeat-safe update without that switch.
7. Run the live AI validation only after separate confirmation:

   ```powershell
   .\database\Setup-CaldovaDatabase.ps1 -TestFoundryAi
   ```

8. Build the application. Start `app\run.ps1` as a long-running process only
   when the user asks to launch it.

## Preflight

Perform checks without repairing or provisioning:

1. Confirm the application responds at `http://localhost:5099`.
2. Confirm `/api/health` reports `Healthy` for `CaldovaRegionalCare`.
3. Confirm the MSSQL extension can connect to `localhost` and database
   `CaldovaRegionalCare`.
4. Confirm the Azure portal is already signed in and the Azure Local VM, AKS
   cluster, and Azure Virtual Desktop resources are ready to show.
5. Confirm Phi-3.5 Mini appears in the VS Code model picker. Do not send a
   clinical prompt.
6. Report each gate as `PASS`, `FAIL`, or `NOT CHECKED`. Stop on a failed gate
   and offer the smallest relevant repair from the documented scripts.

## Rehearse

Follow the runbook's locked order exactly:

1. Transfer Center application.
2. Azure portal: Azure Local VM, AKS, and Azure Virtual Desktop.
3. VS Code MSSQL connection and ordered database scripts.
4. Native RegEx extraction.
5. Approved `ai.Skill` row.
6. Transfer-skill procedure, JSON payload, and
   `sys.sp_invoke_external_rest_endpoint`.
7. Phi-3.5 Mini in VS Code Chat.

For each beat, present only its **Say**, **Show**, and **Land** guidance, then
wait for the user to continue. Do not execute setup or repair commands during a
rehearsal. Do not expose credential rows when showing endpoint metadata.

## Troubleshoot

- Start from the failed gate and its exact error.
- Read the owning script before proposing a change.
- Prefer rerunning a documented validation over changing infrastructure.
- Do not use `Connect-AksArc.ps1` unless direct kubeconfig access failed and the
  user explicitly asks to troubleshoot Arc Cluster Connect.
- End with the failed command, the evidence found, and the next documented
  action.

## Completion Report

Report the selected mode, checks performed, commands run, gates passed, and any
remaining manual step. Never include secret values in the report.