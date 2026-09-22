<!-- MACHINE-OPTIMIZED -->
# Demo Version 1: From Problem to Answer

> A two-minute SQLCon Barcelona corenote demo using a poorly written WideWorldImporters query that a coworker sent for help.

## For the Demoer

### Demo Description

A coworker sends you difficult-to-read SQL and asks for help. In one continuous SSMS workflow, you connect to the database, format the SQL, run it, inspect the results and execution plan, and ask GitHub Copilot Agent Mode to recommend performance improvements.

The scenario is relatable without manufacturing a slow database: everyone has received SQL that is hard to read, understand, and improve.

The storyboard is the hard two-minute cut. A live Agent Mode response may push the runtime closer to 2:30, so rehearse both the live path and the immediate screenshot fallback.

### Features Demonstrated

- Connection dialog improvements
  - Custom connection names
  - Favorite connections
- Object Explorer improvements
  - Group by Schema, shown briefly without browsing
- SQL Formatter
- Results experience improvements
  - Execution plans in separate tabs
  - Results-grid zoom
- GitHub Copilot in SSMS
  - Agent Mode

### Story

> **A coworker sent me this SQL. Let's make it readable, see what it does, and make it better.**

The demoer:

1. Connects to WideWorldImporters through a custom-named favorite.
2. Opens the difficult-to-read coworker query.
3. Uses SQL Formatter to make the query readable.
4. Runs the query.
5. Opens the execution plan in its separate tab.
6. Briefly enlarges the results grid.
7. Asks Agent Mode to analyze the same query and recommend performance improvements.

Object Explorer remains visible with **Group by Schema** enabled, but there is no prolonged folder navigation. The query, not the database setup, drives the story.

### Prerequisites

#### Outside SSMS

- [ ] Follow the [public environment setup guide](../setup/README.md).
- [ ] Use a supported Windows environment. The recording used a Windows virtual machine with SSMS 22.10.2.
- [ ] Install the GitHub Copilot component for SSMS.
- [ ] Use a GitHub Copilot account with an active entitlement.
- [ ] Provision either SQL Server or Azure SQL Database where it is reachable from the demo environment.
- [ ] Restore or deploy the WideWorldImporters sample database.
- [ ] Run [00-setup-performance-demo.sql](../assets/version-1/00-setup-performance-demo.sql) against WideWorldImporters.
- [ ] Run [90-validate-performance-demo.sql](../assets/version-1/90-validate-performance-demo.sql) with actual execution plans enabled.
- [ ] Confirm the original and optimized queries return the same five rows.
- [ ] Confirm the non-SARGable query produces a visibly less efficient plan than the date-range query.
- [ ] Grant the demo login permission to connect, browse the required objects, run the read-only query, and view the actual execution plan.
- [ ] Copy [coworker-sales-query.sql](../assets/version-1/coworker-sales-query.sql) to the demo machine without reformatting it.
- [ ] Keep [optimized-sales-query.sql](../assets/version-1/optimized-sales-query.sql) available as the expected optimization reference.


#### Within SSMS

- [ ] Sign in to GitHub Copilot.
- [ ] Open Copilot Chat and select Agent Mode.
- [ ] Set the Modern connection dialog to the horizontal layout.
- [ ] Add the WideWorldImporters connection to **Favorite Connections** with Custom Name `WWI - SQLCon Demo`.
- [ ] Confirm the favorite contains no sensitive server, tenant, user, or credential information.
- [ ] Turn on **Group by Schema** in Object Explorer.
- [ ] Add `coworker-sales-query.sql` to the recent-files list and verify it can be opened with one quick action.
- [ ] Confirm the unformatted query fits on screen without scrolling.
- [ ] Enable **Include Actual Execution Plan**.
- [ ] Confirm the results-grid zoom interaction works and is visually obvious at approximately 150%.
- [ ] Confirm the execution plan opens in a separate tab.
- [ ] Confirm the plan shows a stable, easy-to-identify scan or inefficient access pattern.
- [ ] Apply SQL Formatter and confirm the query remains functionally unchanged.
- [ ] Run the Agent Mode prompt and confirm the response fits on screen without scrolling.
- [ ] End with Object Explorer disconnected so the connection step remains visible.

## The Demo

### Two-Minute Storyboard

| Time | Step | On-screen action | Story beat | Product message | Demo note |
| --- | --- | --- | --- | --- | --- |
| 0:00-0:06 | Open | Show SSMS ready on the desktop | "A coworker sent me this SQL. Let's make it readable, see what it does, and make it better." | SSMS supports the full workflow from inherited SQL to a recommended improvement | Start with no unrelated windows visible |
| 0:06-0:18 | 1. Connect | In the horizontal Modern connection dialog, select `WWI - SQLCon Demo` from **Favorite Connections** and connect | Open the shared environment | The connection experience is more personal and efficient | Let the layout and custom favorite speak for themselves |
| 0:18-0:22 | Ambient Object Explorer | Let the schema-grouped `Sales` objects remain visible | Orient without interrupting the story | Object Explorer can organize objects around the database's schema | Do not click through folders or explain the feature |
| 0:22-0:34 | 2. Open SQL | Open `coworker-sales-query.sql` from recent files | "Here is the query they sent." | SSMS is the familiar place to review T-SQL | Do not explain the query yet |
| 0:34-0:48 | 3. Format | Say, "First, let's make this readable," then apply SQL Formatter | Turn inherited SQL into reviewable SQL | Built-in formatting removes immediate friction | Pause only long enough for the before-and-after to register |
| 0:48-1:00 | 4. Run | Execute the formatted query with the actual plan enabled | Run the inherited query | Query execution remains central to the SSMS workflow | Move directly to the plan when execution completes |
| 1:00-1:10 | 5. Show plan | Select the separate execution-plan tab and hold for a moment on the scan or inefficient access pattern | Move from execution to performance evidence | Results and execution plans are easier to inspect in separate tabs | Do not explain plan operators in detail |
| 1:10-1:18 | 6. Enlarge results | Return to the results grid and increase its zoom to approximately 150% | Make the result easy to inspect | Grid results can be enlarged independently for readability | One visual action; do not discuss rows or open export menus |
| 1:18-1:52 | 7. Use Agent Mode | Return to the formatted query, switch to Copilot, and submit the prepared prompt | "Rather than manually interpreting this plan, let's have Agent Mode investigate it." | Agent Mode can use the active SSMS context to continue the investigation | If the response misses the rehearsed cutoff, show the screenshot immediately |
| 1:52-2:00 | Close | Hold on the concise recommendation | "From coworker SQL to a clear next step, all inside SSMS." | Familiar tools and AI assistance work together | Do not add another feature summary |

### Step-by-Step Instructions

#### Before Starting

1. Start SSMS with Object Explorer visible but disconnected.
2. Confirm the Modern connection dialog will open in horizontal layout.
3. Confirm `coworker-sales-query.sql` appears in recent files.
4. Confirm Copilot Chat is signed in and Agent Mode is selected.
5. Keep the Agent Mode fallback screenshot one action away.

#### 1. Connect

1. Open the Modern connection dialog.
2. In **Favorite Connections**, select `WWI - SQLCon Demo`.
3. Connect without explaining the connection features.
4. Allow the horizontal layout, custom name, and favorite placement to demonstrate the improvements visually.
5. When Object Explorer connects, let the expanded `Sales` schema group remain visible for approximately four seconds.
6. Do not browse through additional folders.

#### 2. Open the Coworker SQL

1. Open [coworker-sales-query.sql](../assets/version-1/coworker-sales-query.sql) from recent files.
2. Say:

> Here is the query they sent.

3. Pause briefly so the audience can register the poor formatting.
4. Do not explain joins, predicates, or expected results.

Prepared unformatted query:

```sql
select top 5 o.CustomerID,sum(ol.Quantity*ol.UnitPrice) as SalesValue from Sales.Orders o join Sales.OrderLines ol on o.OrderID=ol.OrderID where year(o.OrderDate)=2015 group by o.CustomerID order by SalesValue desc;
```

#### 3. Format the Query

Say:

> First, let's make this readable.

Then:

1. Keep `coworker-sales-query.sql` active.
2. Invoke **Format Document** using the menu or keyboard shortcut verified for the event build.
3. Pause briefly on the formatted result.

Expected formatted shape:

```sql
SELECT TOP 5
    o.CustomerID,
    SUM(ol.Quantity * ol.UnitPrice) AS SalesValue
FROM Sales.Orders AS o
JOIN Sales.OrderLines AS ol
    ON o.OrderID = ol.OrderID
WHERE YEAR(o.OrderDate) = 2015
GROUP BY o.CustomerID
ORDER BY SalesValue DESC;
```

The exact formatter output can vary with configured preferences. It must preserve query behavior while making casing, indentation, and line breaks consistent.

The expected optimized predicate is available in [optimized-sales-query.sql](../assets/version-1/optimized-sales-query.sql).

#### 4. Run the Query

1. Confirm **Include Actual Execution Plan** is enabled.
2. Run the query.
3. When execution completes, move directly to the execution-plan tab.

#### 5. Show the Execution Plan

1. Select the separate execution-plan tab.
2. Hold for a moment on the scan or inefficient access pattern.
3. Do not walk through plan operators.
4. Return to the results grid.

#### 6. Enlarge the Results Grid

1. Increase the results-grid zoom to approximately 150% using the interaction verified for the event build.
2. Let the visual change register.
3. Do not explain individual rows or values.
4. Return to the formatted query.

#### 7. Ask Agent Mode

Say:

> Rather than manually interpreting this plan, let's have Agent Mode investigate it.

1. Open the prepared Copilot Chat surface.
2. Confirm Agent Mode is selected.
3. Copy and paste this prompt:

```text
Analyze this query and recommend performance improvements. Explain the most important change first.
```

4. Submit the prompt.
5. If the live response is not ready within 10 seconds, switch immediately to the full-screen screenshot.
6. Hold on the response while highlighting the non-SARGable date predicate and recommended date range.

A successful response:

1. Identifies the function applied to `Sales.Orders.OrderDate` as non-SARGable.
2. Explains that it can prevent an efficient index seek and contribute to the scan shown in the plan.
3. Recommends replacing it with an explicit date range.
4. Avoids recommending an index change without validating the broader workload.

#### Close

Say:

> From coworker SQL to a clear next step, all inside SSMS.

## Appendix

### Resolved Decisions

| Decision | Resolution |
| --- | --- |
| Story | "A coworker sent me this SQL" |
| Sample database | WideWorldImporters |
| SSMS version | 22.10.2 |
| Connection treatment | Show the horizontal Modern connection dialog and select a custom-named favorite without explaining the features |
| Object Explorer treatment | Keep **Group by Schema** enabled and visible for approximately four seconds; do not browse folders |
| Query treatment | Open the poor SQL, format it, run it, and use the same active query for Agent Mode |
| Results-grid enhancement | Increase independent grid zoom to approximately 150% |
| Results discussion | Do not discuss individual rows or values |
| Performance evidence | Show the actual execution plan in its separate tab without explaining operators |
| Demo query | Join `Sales.Orders` and `Sales.OrderLines`; filter with `YEAR(o.OrderDate) = 2015`; return the top five customers by `SalesValue` |
| Demo SQL file | `coworker-sales-query.sql` |
| SQL assets | Setup, stage query, optimized reference, validation, and teardown scripts under [`assets/version-1/`](../assets/version-1/) |
| Query duration | Three seconds maximum |
| Agent Mode prompt | `Analyze this query and recommend performance improvements. Explain the most important change first.` |
| Agent Mode expected result | Identify the non-SARGable predicate, explain its plan impact, and recommend an explicit date range |
| Live or fallback | Live first; switch to a full-screen screenshot after 10 seconds; short recording is the secondary fallback |

### Open Decisions

| Remaining decision | Recommendation |
| --- | --- |
| Exact formatter command | Record the menu path and keyboard shortcut verified in the final event build |
| Results-grid zoom interaction | Record the exact control or shortcut verified in the final event build |
| Agent Mode screenshot transition | Agree with production on the fastest way to switch without exposing the desktop |

### Next Detail Pass

1. Validate the result set and execution-plan shape in the final event database.
2. Add a representative Agent Mode response.
3. Finalize the exact formatter command and results-grid zoom interaction.
4. Add the final fallback screenshot and recording links.
5. After the event, run [99-teardown-performance-demo.sql](../assets/version-1/99-teardown-performance-demo.sql) if the demo-only index is no longer needed.
