---
name: keynote-demo-app
description: Build or extend a SQLCon EU 2026 keynote demo application so it looks and behaves like the other keynote apps. Use when creating a new demo view (invoices, operations, orders), restyling an existing app to match, adding a deliberate database anti-pattern for a troubleshooting demo, or wiring an app to Azure SQL or Fabric SQL with managed identity. Triggers include "make this look like the keynote app", "build a demo view", "add the slow query demo", "match Caldova styling".
---

# Keynote demo app

Two keynote demos share one product identity. Demo 2 shows evidence search on Azure SQL
Hyperscale. Demo 3 shows a different view of the same product running slowly, then fixed.
They must read as one application. This skill is how you keep that true.

## Non-negotiables

1. **Import the shared tokens.** Never invent colours or fonts.
   ```css
   @import '../../shared/design-system/tokens.css';
   ```
   Palette: canvas `#f8f9f6`, ink `#183129`, forest `#1b5343`, coral `#e27156`.
   Type: Manrope for UI, Newsreader for headings, DM Mono for anything numeric or SQL.

2. **Reuse the layout skeleton.** Sticky `.topbar` with `.brand` + `.brand-mark`, a centred
   `.workspace`, an `.eyebrow` above the `h1`, and a `.metric-band` for live numbers.

3. **Show the SQL.** Every keynote app has a tab or panel that displays the exact
   parameterized statement it just ran. The audience needs to see it is real SQL.

4. **Never fake a number.** If the database is unreachable or a contract check fails, render
   `--` and say so. Do not interpolate, estimate, or reuse a previous value. This rule cost
   real work in demo 2 and it is the reason the demo is trustworthy.

5. **Parameterize everything.** No string-concatenated SQL, ever. It is both a security
   issue and the subject of demo 3.

## Building a new view

Start from `demo3-estate-running-itself/app`. It is deliberately small: a Vite React client,
an Express API, and one SQL module. Copy it, rename the entity, keep the shell.

Structure to preserve:

```
app/
  server/index.ts     Express API. One route per screen. Parameterized queries only.
  src/App.tsx         One page. Search control, metric band, results table, SQL panel.
  src/App.css         View-specific styles only. Tokens come from shared/.
```

## Connecting to the database

Use Microsoft Entra authentication and a managed identity. Never put a SQL login in code
or in an environment file.

```ts
import { DefaultAzureCredential } from '@azure/identity'
import sql from 'mssql'              // NOTE: default import. mssql is CommonJS.
import type * as MSSQL from 'mssql'  // types only

const token = await new DefaultAzureCredential().getToken('https://database.windows.net/.default')
const pool = await new sql.ConnectionPool({
  server: process.env.AZURE_SQL_SERVER,
  database: process.env.AZURE_SQL_DATABASE,
  authentication: { type: 'azure-active-directory-access-token', options: { token: token.token } },
  options: { encrypt: true, trustServerCertificate: false },
}).connect()
```

Grant the identity a least-privilege role, not `db_owner`:

```sql
CREATE USER [my-app-identity] FROM EXTERNAL PROVIDER;
ALTER ROLE MyAppReader ADD MEMBER [my-app-identity];
```

## Known traps

These cost hours during demo 2. Do not rediscover them.

- `import * as sql from 'mssql'` compiles but throws `sql.ConnectionPool is not a constructor`
  at runtime. mssql is CommonJS with no ESM named exports. Use a default import.
- `COUNT_BIG` comes back as a **string** through tedious. `count === 1000` is always false.
  Wrap in `Number()`.
- `CAST(vector AS NVARCHAR(MAX))` is lossy at about 8 significant digits, so it cannot verify a
  float32 round trip. Compare vectors in-engine with `VECTOR_DISTANCE('euclidean', a, b) = 0`.
- Docker `COPY` preserves restrictive host file permissions. If files come from OneDrive, add
  `COPY --chown=node:node` and `chmod`, or the container fails with `EACCES`.
- A Container Apps job with a system-assigned identity cannot pull its own first image. Create a
  user-assigned identity, grant `AcrPull`, then reference it with `--registry-identity`.

## Adding a deliberate anti-pattern

Demo 3 needs a query that is slow for a reason a human can explain in one sentence. The
approved one is a parameter type mismatch that forces a scan instead of a seek.

Make the column and the parameter disagree:

```sql
CREATE TABLE dbo.Invoice (InvoiceNumber VARCHAR(20) NOT NULL, ...);
CREATE NONCLUSTERED INDEX IX_Invoice_InvoiceNumber ON dbo.Invoice (InvoiceNumber);
```

```ts
// Slow: NVarChar parameter against a VARCHAR column forces CONVERT_IMPLICIT on every row.
request.input('invoiceNumber', sql.NVarChar(20), value)

// Fixed: matching type allows an index seek.
request.input('invoiceNumber', sql.VarChar(20), value)
```

The fix is one word in the application. That is the point of the demo: the database was
never wrong, and nobody had to change the schema.

Keep both paths in the code behind a config flag so the before and after can be shown live
without editing files on stage.

## Writing copy for the app

Match the house voice: short sentences, plain English, direct address. Say "1,000 chunks"
not "a corpus of approximately one thousand document fragments". Avoid "leverage",
"seamless", "powerful", and "exciting".
