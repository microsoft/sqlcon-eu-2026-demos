# Set Up the Version 1 SSMS Demo

This guide recreates the recorded "From Problem to Answer" demo. The recording used SSMS 22.10.2 in a Windows virtual machine and Azure SQL Database. You do not need the same hosting model, service tier, resource names, subscription, or identity.

Use whichever disposable environment is easiest:

- SQL Server 2016 or later on Windows, Linux, or a container
- Azure SQL Database

The database engine can run anywhere SSMS can reach it. SSMS itself runs on Windows, including a Windows virtual machine.

## 1. Install the Tools

1. Install [SQL Server Management Studio 22](https://learn.microsoft.com/ssms/install/install) on a supported Windows environment.
2. Include the GitHub Copilot component during installation or add it through the Visual Studio Installer.
3. Sign in with a GitHub account that has access to Copilot.
4. Confirm that Copilot Chat opens and that Agent Mode is available.

## 2. Prepare WideWorldImporters

Download the WideWorldImporters OLTP sample that matches your target. Microsoft provides a backup for SQL Server and a BACPAC for Azure SQL Database in the [WideWorldImporters installation guide](https://learn.microsoft.com/sql/samples/wide-world-importers-oltp-install-configure).

Choose one path:

### SQL Server

Restore the WideWorldImporters backup in SSMS. The Full sample on Developer or Enterprise edition gives the richest Object Explorer view, but the demo only depends on `Sales.Orders`, `Sales.OrderLines`, and 2015 order data.

### Azure SQL Database

Import the WideWorldImporters BACPAC using **Import Data-tier Application** in SSMS. Any service tier that completes the queries within your presentation timing is sufficient. Hyperscale is not required.

Keep the database name `WideWorldImporters`. The supplied scripts select that database explicitly.

## 3. Prepare the Query

Connect to `WideWorldImporters` with an account that can select from the `Sales` schema, view execution plans, and create the temporary demo index. Then run these scripts in order:

1. [`00-setup-performance-demo.sql`](../assets/version-1/00-setup-performance-demo.sql)
2. [`90-validate-performance-demo.sql`](../assets/version-1/90-validate-performance-demo.sql) with **Include Actual Execution Plan** enabled

Confirm before rehearsing:

- Both validation queries return the same five rows in the same order.
- The `YEAR(o.OrderDate) = 2015` query reads more rows or shows a less efficient access pattern than the explicit date-range query.
- Each query finishes comfortably within the allotted demo time.

Exact runtimes and plan operators can vary by SQL Server version, service tier, statistics, cache state, and sample edition. Use the visible difference in your own environment rather than quoting the recording's measurements.

## 4. Prepare SSMS

1. Save [`coworker-sales-query.sql`](../assets/version-1/coworker-sales-query.sql) locally without formatting it.
2. Add the file to the SSMS recent-files list.
3. Add the database connection to **Favorite Connections** with a clear custom name such as `WWI - SQLCon Demo`.
4. Turn on **Group by Schema** in Object Explorer and leave the `Sales` group visible.
5. Enable **Include Actual Execution Plan**.
6. Verify the SQL Formatter command, execution-plan tab, and results-grid zoom interaction in your installed SSMS build.
7. Open Copilot Chat, select Agent Mode, and prepare this prompt:

```text
Analyze this query and recommend performance improvements. Explain the most important change first.
```

## 5. Rehearse

Follow the [Version 1 storyboard](../demo/version-1-from-problem-to-answer.md). Rehearse once with a live Agent Mode response and once with a screenshot fallback. The successful response should identify the non-SARGable `YEAR` predicate and recommend an explicit date range before suggesting broader index changes.

For a clean opening frame, disconnect Object Explorer after rehearsal and leave no unrelated windows or connection details visible.

## Security and Sharing

- Use sample data only.
- Do not publish server names, subscription IDs, tenant details, user names, IP addresses, passwords, tokens, or saved SSMS connection profiles.
- Prefer Microsoft Entra authentication for Azure SQL Database. Use encrypted connections and keep **Trust server certificate** off.
- Grant only the permissions required to prepare and present the demo. Remove temporary access after the event.

## Cleanup

Run [`99-teardown-performance-demo.sql`](../assets/version-1/99-teardown-performance-demo.sql) to remove the demo-only date index. Delete the disposable database or hosting resources when they are no longer needed to avoid ongoing cost.