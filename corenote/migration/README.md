# Nandiyo Logistics migration lab

Nandiyo Logistics is a fictional ASP.NET Core 8 MVC order-fulfillment application
backed by SQL Server. This lab demonstrates how to assess and replatform the
application to Linux Azure App Service and its database to Azure SQL Database
Hyperscale.

The completed solution uses:

- ASP.NET Core 8 on Linux Azure App Service
- Azure SQL Database Hyperscale
- Microsoft Entra-only SQL authentication
- An App Service system-assigned managed identity
- An offline BACPAC migration
- An App Service health check at `/health`

> [!WARNING]
> This lab creates billable Azure resources and enables public network access to the
> Azure SQL logical server. Use a nonproduction subscription, remove the temporary
> migration firewall rule immediately after import, and delete the resource group when
> you finish.

## Business workflows

1. **Order intake** reserves inventory and creates a customer commitment.
2. **Fulfillment control** advances orders from Submitted to Processing to Fulfilled.
3. **Inventory risk** compares stock with open commitments.
4. **Partner performance** reports account value and order history.

The deterministic seed creates 18 customers, 24 products, 60 orders, and 120 order
items.

## Choose a starting point

- Use the current branch to inspect or deploy the completed migration.
- Use the `corenote-migration-baseline` tag to repeat the assessment and remediation
  from the original application.

From the repository root, create a separate baseline worktree:

```powershell
git worktree add ..\sqlcon-migration-baseline corenote-migration-baseline
Set-Location ..\sqlcon-migration-baseline\corenote\migration
```

Do not deploy the baseline infrastructure. Return to the current branch before
provisioning Azure.

## Run locally

Requirements:

- Windows with SQL Server LocalDB
- .NET 8 SDK
- `sqlcmd`

```powershell
dotnet restore FictionalOps.sln
dotnet build FictionalOps.sln --configuration Release
dotnet run --project src\FictionalOps.Web
```

The application creates and seeds the local `Operations` database on first startup.
Stop the application with <kbd>Ctrl</kbd>+<kbd>C</kbd> before changing or exporting
the database.

## Reproduce the migration

Follow [the end-to-end migration workshop](docs/ONE-HOUR-AZURE-MODERNIZATION-WORKSHOP.md)
for the complete sequence:

1. Create the local baseline and intentional SQL compatibility findings.
2. Assess the application and SQL Server database.
3. Apply and validate the focused remediations.
4. Provision App Service and an Entra-only Azure SQL logical server.
5. Export and import `Operations` with a BACPAC.
6. Grant the App Service managed identity database access.
7. Deploy and validate all application workflows.
8. Remove temporary access and clean up Azure resources.

## Repository layout

| Path | Purpose |
|---|---|
| `src/FictionalOps.Web` | ASP.NET Core MVC application |
| `database/assessment` | Read-only Azure SQL readiness inventory |
| `database/legacy-cross-database-reporting.sql` | Creates the intentional SQL Server compatibility findings |
| `database/remediation` | Idempotent source-database remediation |
| `infra/main.bicep` | App Service and Azure SQL infrastructure |
| `skills` | SQL migration and assessment skills used by the guided workflow |
| `docs/ONE-HOUR-AZURE-MODERNIZATION-WORKSHOP.md` | Complete replication guide |

Generated build, browser-library, publish, and BACPAC artifacts are intentionally
excluded from source control.

## Production considerations

The template favors a repeatable lab over a production network design. Before using
the pattern for a real workload, evaluate private endpoints, restricted outbound
access, deployment slots, monitoring, backup retention, threat protection, availability
requirements, and CI/CD.
