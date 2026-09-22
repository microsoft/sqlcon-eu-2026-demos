<!-- MACHINE-OPTIMIZED -->
# Demo Version 2: Five Customer Asks We Delivered

> A rapid-fire, two-minute SQLCon Barcelona corenote highlight reel using SSMS 22.10.2.

## For the Demoer

### Demo Description

This demo moves quickly through five improvements shaped by customer feedback. Unlike Version 1's continuous story, this version prioritizes breadth, visible product progress, and applause moments.

Each feature gets one clear visual action. Avoid explaining setup, completing long workflows, or ranking the requests.

### Features Demonstrated

1. Better connection management
   - Saved connections
   - Search and filtering
   - Connection import and export
2. Better Object Explorer
   - Group by Schema
3. Better results experience
   - Excel, JSON, Markdown, and XML export formats
4. Built-in SQL Formatter
5. GitHub Copilot in SSMS
   - Agent Mode

### Story

> **You asked us to make the everyday SSMS experience better. Here are five ways we delivered.**

The demoer:

1. Shows how connections are easier to find, organize, and move.
2. Groups Object Explorer objects by schema.
3. Shows the expanded results export formats.
4. Applies the built-in SQL Formatter.
5. Ends with GitHub Copilot Agent Mode using the active SSMS context.

Describe these as customer-driven improvements. Do not call them the five highest-voted or top five requests unless the final public repository includes evidence supporting that exact ranking.

### Prerequisites

#### Outside SSMS

- [ ] Use a Windows demo machine with SSMS 22.10.2 installed.
- [ ] Install the GitHub Copilot component for SSMS.
- [ ] Use a GitHub Copilot account with an active entitlement.
- [ ] Provision a SQL Server instance that is reachable from the demo machine.
- [ ] Restore WideWorldImporters as the synthetic demo database, with multiple schemas such as `Sales`, `Purchasing`, and `Warehouse` and enough objects to demonstrate **Group by Schema**.
- [ ] Run [00-validate-environment.sql](../assets/version-2/00-validate-environment.sql) against WideWorldImporters.
- [ ] Grant the demo login permission to connect, browse the required objects, and run the prepared read-only query.
- [ ] Use [results-export-query.sql](../assets/version-2/results-export-query.sql) as the saved results query; confirm it returns five deterministic rows with recognizable `CustomerName`, `OrderCount`, and `SalesValue` columns.
- [ ] Copy [formatter-input.sql](../assets/version-2/formatter-input.sql) to the demo machine without reformatting it.
- [ ] Prepare a recording environment optimized for capture quality, including display scaling, fonts, theme selection, notifications disabled, and removal of unrelated applications.

#### Within SSMS

- [ ] Create several public-safe saved connections, including the primary WideWorldImporters connection named `WWI - SQLCon Demo`.
- [ ] Configure the Object Explorer starting state required by the recording.
- [ ] Configure and validate SQL Formatter behavior for the recording.
- [ ] Open or run [results-export-query.sql](../assets/version-2/results-export-query.sql) so the grid is ready for the demo.
- [ ] Open [formatter-input.sql](../assets/version-2/formatter-input.sql) and confirm the before-and-after fit on screen.
- [ ] Configure and validate GitHub Copilot Agent Mode using the final demo prompt and verify the response fits onscreen.
- [ ] Close unrelated tabs, servers, notifications, and tool windows.
- [ ] Confirm no real server names, tenant names, usernames, credentials, or connection strings are visible.
- [ ] Rehearse the full reel from a clean start in 1:45 or less.

## The Demo

### Two-Minute Storyboard

| Time | Step | On-screen action | Story beat | Product message | Demo note |
| --- | --- | --- | --- | --- | --- |
| 0:00-0:08 | Open | Show SSMS with the demo environment ready | "You asked us to make the everyday SSMS experience better. Here are five ways we delivered." | Customer feedback shapes SSMS | Do not call these the top five requests |
| 0:08-0:28 | 1. Better connection management | Show saved connections and search/filter, then point to import/export | Find, organize, and carry connections between environments | The connection experience is more flexible and portable | Do not perform a full import during the recording |
| 0:28-0:48 | 2. Better Object Explorer | Toggle **Group by Schema** | Turn one long object list into the structure the database already uses | Object Explorer better supports databases with many objects | Keep the target database expanded |
| 0:48-1:08 | 3. Better results experience | Open **Save Results As** and reveal Excel, JSON, Markdown, and XML | Move results directly into the needed format | The results grid supports more practical output workflows | Do not complete the file-save flow |
| 1:08-1:28 | 4. Built-in formatter | Apply SQL Formatter to the prepared query | Transform difficult-to-read SQL | Formatting is built into the query editor | Pause only long enough for the change to register |
| 1:28-1:52 | 5. Agent Mode | Switch to GitHub Copilot and submit the prepared prompt | Move from question to a recommended next step | Agent Mode can use active SSMS context | Use a recorded take in which the response fits the timing and screen |
| 1:52-2:00 | Close | Hold on the concise Agent Mode response | "Five customer-driven improvements, all in the SSMS workflow you already know." | Everyday improvements and AI assistance work together | Do not add another feature explanation |

### Step-by-Step Instructions

#### Before Starting

1. Start SSMS with the connection experience ready to open.
2. Confirm the saved connections use only public-safe names.
3. Confirm Object Explorer is connected to the demo database with **Group by Schema** turned off.
4. Confirm `results-export-query.sql` and its result grid are one action away.
5. Confirm `formatter-input.sql` is open or one action away.
6. Confirm Copilot Chat is signed in and Agent Mode is selected.

#### 1. Show Better Connection Management

1. Open the connection experience.
2. Show the prepared saved connections.
3. Search for `SQLCon` and show `WWI - SQLCon Demo`.
4. Point to connection import/export.
5. Do not perform a full import or export.
6. Avoid exposing real server names, tenant names, usernames, or connection strings.

#### 2. Show Better Object Explorer

1. Return to the expanded demo database in Object Explorer.
2. Show the ungrouped object list.
3. Toggle **Group by Schema**.
4. Pause briefly on the grouped result.
5. Do not browse through schemas or objects.

#### 3. Show the Better Results Experience

1. Show the prepared result set from [results-export-query.sql](../assets/version-2/results-export-query.sql).
2. Open **Save Results As**.
3. Show the Excel, JSON, Markdown, and XML choices.
4. Do not complete the file-save flow.

#### 4. Show the Built-in SQL Formatter

1. Open [formatter-input.sql](../assets/version-2/formatter-input.sql).
2. Pause briefly so the audience can register the original formatting.
3. Invoke **Format Document** using the menu or keyboard shortcut verified for SSMS 22.10.2.
4. Pause briefly on the formatted result.
5. Do not adjust formatter settings during the recording.

#### 5. Show GitHub Copilot Agent Mode

1. Keep the relevant query or database context active.
2. Open Copilot Chat.
3. Confirm Agent Mode is selected.
4. Copy and paste the final prompt:

```text
Review this query. Explain what it does and suggest one way to validate its performance, in three concise bullets.
```

5. Submit the prompt.
6. Hold on the concise response.

#### Close

Say:

> Five customer-driven improvements, all in the SSMS workflow you already know.

## Appendix

### Resolved Decisions

| Decision | Resolution |
| --- | --- |
| Format | Rapid-fire highlight reel |
| Framing | Five customer asks we delivered |
| Duration | Two-minute hard cut; rehearse to 1:45 |
| SSMS version | 22.10.2 |
| Demo database | WideWorldImporters |
| Feature categories | Connection management, Object Explorer, results, SQL Formatter, and GitHub Copilot Agent Mode |
| Claim language | Customer-driven improvements; do not claim a ranked top five without evidence |
| Connection action | Show saved connections, search/filter, and point to import/export without performing it |
| Connection name and search | Save `WWI - SQLCon Demo`; search for `SQLCon` |
| Object Explorer action | Toggle **Group by Schema** |
| Results action | Show Excel, JSON, Markdown, and XML under **Save Results As** |
| Results query | [`results-export-query.sql`](../assets/version-2/results-export-query.sql) |
| Formatter action | Format [`formatter-input.sql`](../assets/version-2/formatter-input.sql) |
| Agent Mode action | Ask Agent Mode to explain the formatted query and suggest one way to validate its performance |

### Open Decisions

| Remaining decision | Recommendation |
| --- | --- |
| Results format emphasis | Highlight Markdown for the GitHub-repository tie-in, with Excel as the familiar audience cue |
| Exact formatter command | Record the menu path and keyboard shortcut verified in SSMS 22.10.2 |
| Feature labels | Validate GA versus preview language before publication |

### Next Detail Pass

1. Validate all scripts against the final WideWorldImporters restore.
2. Add the expected result set and representative Agent Mode response.
3. Record exact clicks and keyboard actions verified in SSMS 22.10.2.
