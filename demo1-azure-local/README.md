# Caldova Regional Care on Azure Local

This folder contains the complete SQLCon Europe 2026 keynote demo kit for
Caldova Regional Care. The demo combines SQL Server 2025, Foundry Local on an
AKS Arc cluster hosted by Azure Local, an ASP.NET Core transfer-center
application, ordered SQL deployment scripts, and a guided presenter runbook.

It supports four related experiences:

1. Run the Regional Care Transfer Center application.
2. Demonstrate SQL Server 2025 invoking Foundry Local on Azure Local.
3. Run the same database AI workflow on Azure SQL Database Hyperscale and
  Microsoft Foundry.
4. Register the Azure Local Phi model in VS Code Chat.

## Run with GitHub Copilot

Open the repository in VS Code with GitHub Copilot Chat and select **Agent**
mode. Type `/` and choose:

- `/prepare-keynote-demo-1` to validate prerequisites and guide the documented
  VM setup, database deployment, application build, and health checks.
- `/rehearse-keynote-demo-1` to run non-destructive preflight and walk through
  the locked presenter sequence one beat at a time.

The prompts use the
[Run Keynote Demo 1 skill](../.github/skills/run-keynote-demo-1/SKILL.md).
The skill never displays credential material, does not provision or modify the
existing Azure Local environment, and requires confirmation before elevated,
data-changing, or live-model actions.

The live environment uses the authenticated Azure Local Gateway directly:

```text
https://172.25.29.251/phi-35-mini/v1/chat/completions
```

Caddy is not part of the primary Azure Local path.

## Package layout

This folder is self-contained and can be published as a standalone repository:

```text
<demo-root>/
|-- app/                       # ASP.NET Core application
|-- database/                  # SQL Server deployment and validation
|-- hyperscale-foundry/        # Azure SQL + Microsoft Foundry variant
|-- setup/                     # Existing Azure Local environment setup
|-- DEMO-RUNBOOK.md            # Presenter source of truth
`-- README.md
```

- `database/` contains the ordered deployment and validation scripts
  used to create and configure the live `CaldovaRegionalCare` database.
- `app/` contains the real database-backed web application.
- `setup/` configures the Windows VM to trust and reach the existing
  Foundry Local deployment.
- `hyperscale-foundry/` provisions and validates the cloud-hosted variant.

## Fixed environment contract

| Component | Value |
| --- | --- |
| SQL Server | `localhost` |
| Database | `CaldovaRegionalCare` |
| Compatibility level | `170` |
| AKS namespace | `foundry-local-operator` |
| ModelDeployment | `phi-35-mini` |
| Runtime model ID | `Phi-3.5-mini-instruct-cuda-gpu:2` |
| Gateway IP | `172.25.29.251` |
| Chat endpoint | `https://172.25.29.251/phi-35-mini/v1/chat/completions` |
| Application | `http://localhost:5099` |
| Health endpoint | `http://localhost:5099/api/health` |

The Azure Local model deployment, Gateway IP, certificate, and Kubernetes
secret must already exist. This package consumes them; it does not provision
the Azure Local system, AKS cluster, Foundry Local extension, or Phi model.

## Prerequisites

The infrastructure owner must complete these Microsoft Learn workflows before
using this package:

- [Deploy Azure Local](https://learn.microsoft.com/azure/azure-local/deploy/deployment-introduction).
- [Deploy AKS on Azure Local](https://learn.microsoft.com/azure/aks/aksarc/aks-overview).
- [Deploy Foundry Local as an Azure Arc extension](https://learn.microsoft.com/azure/azure-sovereign-clouds/private/foundry-local/deploy-foundry-local-arc-extension).
- [Deploy a model and run inference](https://learn.microsoft.com/azure/azure-sovereign-clouds/private/foundry-local/deploy-run-first-model).

The demo machine requires:

- Windows VM with network access to the Azure Local Kubernetes API and Gateway.
- SQL Server 2025 running on `localhost`.
- .NET 10 SDK.
- PowerShell, Azure CLI, `kubectl`, `kubelogin`, and `curl.exe`.
- [`sqlcmd`](https://learn.microsoft.com/sql/tools/sqlcmd/sqlcmd-download-install)
  available on `PATH`.
- Protected admin kubeconfig for the existing AKS Arc cluster.
- Permission to administer SQL Server and import a root certificate.
- VS Code with the MSSQL extension for the database demo.

## Protected files and secrets

Place the protected kubeconfig at:

```text
C:\setup\SJ-SQLAI-admin.kubeconfig
```

Never commit or display:

- The kubeconfig contents.
- The `phi-35-mini-api-keys` Kubernetes secret.
- The database-scoped credential secret.
- Database master-key passwords.
- A literal API key in `chatLanguageModels.json`.

## 1. Prepare the VM for the Azure Local Gateway

Copy the contents of `setup/` to `C:\setup`, then add the protected
kubeconfig to that directory. In an elevated PowerShell window:

```powershell
Set-Location C:\setup
Set-ExecutionPolicy -Scope Process RemoteSigned
.\Setup.ps1
```

`Setup.ps1` installs or validates prerequisites, confirms Kubernetes access,
imports the existing Gateway root CA into `LocalMachine\Root`, and restarts SQL
Server. Require exit code 0 and `Setup completed successfully.`

Test the direct SQL-to-model path separately:

```powershell
Set-Location C:\setup
.\test.ps1
```

This test must complete with HTTP 200 through
`sys.sp_invoke_external_rest_endpoint`. A successful `curl` alone is not enough.
See [setup/README.md](setup/README.md) for detailed setup and repair guidance.

## 2. Initialize the database

Run this once when `CaldovaRegionalCare` does not exist:

```powershell
Set-Location <demo-root>
.\database\Setup-CaldovaDatabase.ps1 -InitializeDatabase
```

The wrapper runs scripts `00` through `06`, configures the authenticated Azure
Local endpoint, and refuses to overwrite an existing database.

For an existing database, refresh only the repeat-safe objects:

```powershell
.\database\Setup-CaldovaDatabase.ps1
```

## 3. Test the complete database AI workflow

```powershell
.\database\Setup-CaldovaDatabase.ps1 -TestFoundryAi
```

Success requires HTTP 200, a persisted briefing, and exactly seven grounding
sources. The command also verifies the approved `ReceivingBriefing` skill,
grounded packet, model invocation, response validation, and provenance path.

## 4. Build and run the application

```powershell
dotnet build .\app\Caldova.TransferCenter.csproj
.\app\run.ps1
```

Open `http://localhost:5099` in a separate browser window. Verify
`http://localhost:5099/api/health` reports `Healthy` for
`CaldovaRegionalCare`. See [app/README.md](app/README.md) for the HTTP surface and
connection-string override.

## 5. Run the Hyperscale AI variant

This optional cloud variant reuses the database schema and AI contract with
Azure SQL Database Hyperscale and Microsoft Foundry. It does not use the Azure
Local Phi deployment.

Review [hyperscale-foundry/README.md](hyperscale-foundry/README.md), sign in with
Azure CLI, and run:

```powershell
Set-Location .\hyperscale-foundry
.\Deploy.ps1
```

Run the live Microsoft Foundry invocation only when intended:

```powershell
.\Deploy.ps1 -TestFoundry
```

The wrapper requires `go-sqlcmd` for `ActiveDirectoryDefault` authentication.
It provisions missing resources, applies the shared database scripts, validates
the deployment, and removes its temporary SQL firewall rule.

## 6. Add Phi-3.5 Mini to VS Code Chat

Use the same Foundry Local deployment as the SQL demo.

### Copy the API key securely

Run this locally to place the key on the Windows clipboard without displaying
it:

```powershell
$encoded = kubectl --kubeconfig C:\setup\SJ-SQLAI-admin.kubeconfig `
  -n foundry-local-operator get secret phi-35-mini-api-keys `
  -o 'jsonpath={.data.primary-key}'

[Text.Encoding]::UTF8.GetString(
  [Convert]::FromBase64String($encoded)
) | Set-Clipboard

Remove-Variable encoded
```

Do not print the clipboard or paste the key into source control, terminals,
documentation, or chat.

### Register the custom endpoint

1. Run **Chat: Manage Language Models** in VS Code.
2. Select **Add Models** and then **Custom Endpoint**.
3. Use group `Foundry Local`, display name `Phi-3.5 Mini`, and API type
   **Chat Completions**.
4. Paste the API key only into VS Code's secure prompt.
5. Update the generated `chatLanguageModels.json` model entry to match the
   following configuration. Preserve the generated `${input:...}` secret ID.

```json
[
  {
    "name": "Foundry Local",
    "vendor": "customendpoint",
    "apiKey": "${input:chat.lm.secret.<generated-id>}",
    "apiType": "chat-completions",
    "models": [
      {
        "id": "Phi-3.5-mini-instruct-cuda-gpu:2",
        "name": "Phi-3.5 Mini",
        "url": "https://172.25.29.251/phi-35-mini/v1/chat/completions",
        "toolCalling": true,
        "vision": false,
        "streaming": false,
        "maxInputTokens": 123904,
        "maxOutputTokens": 4096,
        "requestHeaders": {
          "api-key": "${apiKey}"
        }
      }
    ]
  }
]
```

The file belongs to the active VS Code user profile, not this repository. The
default-profile path is:

```text
C:\Users\<user>\AppData\Roaming\Code\User\chatLanguageModels.json
```

Run **Developer: Reload Window**, open **Chat: Manage Language Models**, and make
sure the eye icon for `Phi-3.5 Mini` is enabled. Start a new Ask chat and select
the model.

`toolCalling` must be `true` for VS Code 1.137 to include this custom model in
the chat picker. This deployment accepted a request containing OpenAI tool
definitions but did not return `tool_calls`, so use it only in **Ask mode**. The
flag makes the model picker-eligible; it does not prove Agent-mode capability.

## 7. Run the keynote demo

Complete the preflight and follow [DEMO-RUNBOOK.md](DEMO-RUNBOOK.md). The locked
sequence is:

1. Regional Care Transfer Center application.
2. Azure portal: Azure Local VM, AKS, and Azure Virtual Desktop.
3. VS Code: MSSQL connection and the ordered database scripts.
4. SQL Server 2025 native RegEx extraction.
5. Approved and versioned `ai.Skill` contract.
6. Foundry Local URL, grounded JSON payload, and
   `sp_invoke_external_rest_endpoint`.
7. Phi-3.5 Mini in a VS Code Ask chat.

All displayed care and transfer data is synthetic. Describe this environment as
connected Azure Local, not disconnected Azure Local.

## Validation checklist

- [ ] `C:\setup\Setup.ps1` exits 0.
- [ ] `C:\setup\test.ps1` reaches Foundry Local with HTTP 200.
- [ ] Database initialization or repeat deployment exits 0.
- [ ] The live database AI test persists a briefing and seven sources.
- [ ] The ASP.NET Core project builds with no errors.
- [ ] Application health is `Healthy` at port 5099.
- [ ] `Phi-3.5 Mini` appears in the VS Code Ask model picker.
- [ ] If used, the Hyperscale deployment passes its verification script.
- [ ] The Azure portal resources are open and ready before presenting.
