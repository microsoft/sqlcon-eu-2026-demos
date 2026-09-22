# Caldova Regional Care on Hyperscale and Microsoft Foundry

This variant proves that the Caldova schema, packet construction, approved skill,
model invocation procedure, and validation SQL used in the Azure Local keynote
demo also run in Azure SQL Database Hyperscale. The deployment wrapper executes
the shared SQL files directly from `../database`; it does not maintain
a cloud copy of them.

## Deployed target

| Resource | Value |
| --- | --- |
| Subscription | `AzureSQL_bobward` |
| Resource group | `caldovarg` |
| Region | `westus3` |
| SQL server | `caldova-sqlconeu2026.database.windows.net` |
| Database | `CaldovaRegionalCare` |
| SQL compute | Hyperscale `HS_Gen5_8` |
| Foundry resource | `caldova-foundry-sqlconeu2026` |
| Model deployment | `gpt-4.1-mini` |

The exact Foundry URL and model deployment are written explicitly in
`database/05-configure-foundry-model.sql` so the SQL demo is self-contained and
easy to inspect on stage.

The Azure Local demo uses `Phi-3.5-mini-instruct`. That model's hosted
Microsoft Foundry inference offering retired on August 30, 2025. Its current
successor, `Phi-4-mini-instruct`, was tested but returned prose despite the
skill's bare-JSON instruction, so it is not compatible with the unchanged SQL
response contract. The cloud variant therefore uses `gpt-4.1-mini`; the schema,
packet, skill, request shape, invocation procedure, and response contract remain
shared and unchanged.

The SQL logical server uses Microsoft Entra-only authentication. Its
system-assigned managed identity receives `Cognitive Services OpenAI User` on
the Foundry resource. No model API key is stored in the database or scripts.

## Build

Prerequisites:

- Azure CLI signed in to the target tenant and subscription.
- Permission to create the documented Azure resources and role assignment.
- [go-sqlcmd](https://learn.microsoft.com/sql/tools/sqlcmd/sqlcmd-download-install)
  available on `PATH`. The wrapper uses `ActiveDirectoryDefault` authentication.

From this folder:

```powershell
.\Deploy.ps1
```

The script is idempotent. It provisions missing resources, temporarily permits
the current client IP, deploys the shared database scripts, configures the
Microsoft Foundry endpoint, validates the result, and removes the temporary
firewall rule.

If Azure SQL observes a different NAT address than automatic IP detection,
pass that address explicitly with `-ClientIp`. For an Azure-hosted build agent
whose outbound IP rotates, use `-UseAzureServicesFirewall`; the temporary
Azure-services rule is removed when the script exits.

Run the live model invocation only when intended:

```powershell
.\Deploy.ps1 -TestFoundry
```

## App connection

Run the same app with a passwordless Azure SQL connection override:

```powershell
$env:ConnectionStrings__Caldova = 'Server=tcp:caldova-sqlconeu2026.database.windows.net,1433;Initial Catalog=CaldovaRegionalCare;Encrypt=True;TrustServerCertificate=False;Authentication=Active Directory Default;Application Name=Caldova Transfer Center'
dotnet run --project ..\app\Caldova.TransferCenter.csproj
```

The app machine must have network access to the SQL logical server. `Deploy.ps1`
removes its temporary build firewall rule when deployment finishes.
