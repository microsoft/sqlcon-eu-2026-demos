# Demo 3: Your Data Estate Running Itself

**Slide title:** From estate-wide signal to application fix
**Roles:** a data professional and an application developer
**Through line:** Database Hub shows what needs attention. The Database Agent detects the
slow query. GitHub Copilot explains and recommends. The human decides and acts.

This folder is a starting point, not a finished demo. It gives you an application that
looks like the demo 2 app, a database with a realistic anti-pattern, and the queries that
make the cause visible in SSMS.

If you are presenting the data-professional beat, start with
[docs/presenter-runbook.md](docs/presenter-runbook.md) for the stage path and the
rehearsal gates.

## What the app is

`app/` is the same product as demo 2 in a different view. Demo 2 is the evidence search
screen; this is the operations screen. It shares
[shared/design-system/tokens.css](../shared/design-system/tokens.css), the top bar, the
metric band, and the type scale, so on stage the two look like one product.

The screen does two things: look up an invoice by number, and list the overdue queue.

## The anti-pattern

`dbo.Invoice.InvoiceNumber` is `VARCHAR(20)` with a unique index. The application sends an
`NVARCHAR` parameter. SQL Server has to apply `CONVERT_IMPLICIT` to every row before it can
compare, so the index seek becomes an index scan across the whole table.

The switch lives in one place:

```ts
// server/index.ts
.input('invoiceNumber',
  mode === 'varchar' ? sql.VarChar(20) : sql.NVarChar(20),
  invoiceNumber)
```

Set the default with an environment variable, or override per request while rehearsing:

```bash
INVOICE_PARAMETER_MODE=nvarchar npm start     # slow, the production state
INVOICE_PARAMETER_MODE=varchar  npm start     # fixed

curl 'http://127.0.0.1:8010/api/invoices/INV-0004821993?mode=nvarchar'
curl 'http://127.0.0.1:8010/api/invoices/INV-0004821993?mode=varchar'
```

Both paths stay in the code so the before and after can be shown without editing files
live. For the Copilot beat, delete the ternary and let Copilot propose the fix.

The fix is one word in the application. The schema, the index, and the data never change.
That is the point: the database was not wrong.

## Why this and not pagination

Either scenario works for the story. This one was chosen because:

- The cause is one sentence: the parameter type does not match the column.
- The fix is one word, which keeps the Copilot beat short and believable.
- The plan difference is visually obvious in SSMS: Index Scan becomes Index Seek.
- It is not so trivial that the audience feels talked down to.

If you switch to a pagination scenario later, keep the same shape: one visible symptom,
one explainable cause, one small application change. `GET /api/invoices` already uses
`OFFSET ... FETCH NEXT`, so a deep-paging variant is a small edit.

## Set up

1. **Create a Fabric SQL database** (the Database Hub view in this demo is filtered to
   Fabric SQL, so put this one there). Any Azure SQL database works for rehearsal.

2. **Create the schema and seed it.** Two million invoices makes the scan slow enough to
   feel in the UI without a long seed.

   ```bash
   # In SSMS or your client of choice
   :r database/01-invoice-schema.sql

   python database/02-seed-invoices.py \
     --server <server>.database.windows.net \
     --database <database> \
     --invoices 2000000
   ```

3. **Grant the app identity least privilege.**

   ```sql
   CREATE USER [my-app-identity] FROM EXTERNAL PROVIDER;
   ALTER ROLE db_datareader ADD MEMBER [my-app-identity];
   ```

4. **Run the app.**

   ```bash
   cd app
   npm install
   AZURE_SQL_SERVER=<server>.database.windows.net \
   AZURE_SQL_DATABASE=<database> \
   INVOICE_PARAMETER_MODE=nvarchar \
   npm start
   ```

5. **Confirm the symptom.** With `nvarchar`, the lookup should take seconds and the metric
   band should show it. With `varchar` it should be immediate.

## What to show in SSMS

[database/03-anti-pattern.sql](database/03-anti-pattern.sql) has both statements and a plan
cache query. Run it with actual execution plans on. The slow statement shows an Index Scan
with a `CONVERT_IMPLICIT` predicate; the fixed one shows an Index Seek. The logical read
counts differ by orders of magnitude, which is the number worth pointing at.

## Building more views

If you need another screen, read [shared/SKILL.md](../shared/SKILL.md) and hand it to
Copilot. It has the design rules, the connection pattern, and the traps that cost time
during demo 2 (the `mssql` CommonJS import, `COUNT_BIG` returning a string, Docker file
permissions from OneDrive, and the Container Apps identity ordering).
