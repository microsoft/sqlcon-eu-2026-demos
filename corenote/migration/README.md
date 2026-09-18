# Nandiyo Logistics

**Every order, on course.**

Nandiyo Logistics is a fictional ASP.NET Core MVC order-fulfillment application backed
by SQL Server. It is intentionally designed as a small Azure modernization lab, not a
real company or production system. The technical solution retains the `FictionalOps`
identifier so the baseline and migration assets remain directly comparable.

## Product workflows

1. **Order intake:** select a partner and SKU, validate available inventory, create the
    commercial commitment, and reduce stock in one transaction.
2. **Fulfillment control:** prioritize orders by SLA risk and advance work from Submitted
    to Processing to Fulfilled through a managed queue.
3. **Inventory risk:** compare on-hand stock with open commitments and act on Critical,
    Watch, and Healthy coverage signals.
4. **Partner performance:** rank accounts by lifetime value, review open commitments,
    and drill into a complete Partner 360 order history.

The executive operations brief connects all four workflows with booked revenue, average
order value, fulfillment rate, SLA exposure, partner ranking, and inventory exceptions.

The deterministic seed creates 18 customers, 24 products, 60 orders, and 120 order
items. `Orders` and `OrderItems` are the larger demo tables; reference tables contain a
few tens of rows.

## Run locally

Prerequisites: .NET 8 SDK and SQL Server LocalDB.

```powershell
dotnet restore FictionalOps.sln
dotnet run --project src/FictionalOps.Web
```

The app creates and seeds the `Operations` LocalDB database on first startup. To add
the intentional database migration finding, run:

```powershell
sqlcmd -S "(localdb)\MSSQLLocalDB" -E -i database\legacy-cross-database-reporting.sql
```

Use `docs/DEMO-WALKTHROUGH.md` for the short presenter script or
`docs/ONE-HOUR-AZURE-MODERNIZATION-WORKSHOP.md` for the complete hands-on workshop.
See `docs/MIGRATION.md` for the two findings, remediations, target architecture, and
cutover sequence.

## Deploy the Azure target

```powershell
az group create --name rg-velaforge-demo --location eastus
az deployment group create --resource-group rg-velaforge-demo --template-file infra/main.bicep --parameters sqlAdminLogin=<login> sqlAdminPassword=<secure-value>
dotnet publish src/FictionalOps.Web -c Release -o .\publish
```

Supply secrets interactively or through an approved secret store; do not commit them.