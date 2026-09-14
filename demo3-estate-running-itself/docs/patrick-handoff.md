# Demo 3 handoff for Patrick

## Story in one line

Database Hub finds the estate-wide signal, the Database Agent explains the slow query,
GitHub Copilot proposes the application fix, and the human decides whether to apply it.

## What is ready

- The Caldova operations UI in `app/` matches Demo 2's product identity.
- The default `NVARCHAR` parameter reproduces an implicit-conversion scan against the
  `VARCHAR(20)` invoice number column.
- The `VARCHAR` path is the fixed comparison and produces an index seek.
- `database/03-anti-pattern.sql` contains the before-and-after queries and a plan-cache
  query for rehearsal in SSMS.
- The app supports both paths without a live code edit by adding `?mode=nvarchar` or
  `?mode=varchar` to the lookup API request.

## Patrick's stage path

1. Start in Database Hub and narrow the estate to the database selected for this demo.
2. Open the performance signal for the Caldova invoice lookup.
3. Use the Database Agent to identify the implicit conversion and explain why the seek
   became a scan.
4. Keep the agent boundary explicit: "read only, reversible, and never acts on the database by itself."
5. Hand off to Anna for the application change from `sql.NVarChar(20)` to
   `sql.VarChar(20)`.
6. Return to the signal or execution plan and show that the lookup now seeks with far
   fewer logical reads.

The schema, index, and data do not change. The application parameter type is the fix.

## Rehearsal gates

- Confirm the chosen database appears in Patrick's Database Hub scope.
- Seed enough rows for a visible scan; the current target is two million invoices.
- Run both statements in `database/03-anti-pattern.sql` with actual execution plans and
  `STATISTICS IO` enabled.
- Verify the slow plan shows `CONVERT_IMPLICIT` and an Index Scan.
- Verify the fixed plan shows an Index Seek.
- Record the logical-read difference used on stage; do not quote an unretained number.
- Run the app once in each mode and retain the timings used for rehearsal.
- Rehearse the handoff so diagnosis stays with Patrick and the code decision stays with
  Anna.

## Team decisions still open

- Choose the final Fabric SQL database and confirm it is visible in Database Hub.
- Confirm the final wording and product behavior for the Database Agent beat.

Do not build around a specific latency until the final database and row count are locked.