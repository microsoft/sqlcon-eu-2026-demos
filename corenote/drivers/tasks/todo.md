# SalesLT Connection String Demo

## Goal

Build only clients that accept the exact same connection string without parsing, rewriting, or translating it. Assign the value once to `SQL_CONNECTION_STRING`, then run each client and return the same ordered rows from `SalesLT.Product`.

## Target

```text
Server=0.0.0.0;Database=AdventureWorksLT;UID=<user>;PWD=<password>;Encrypt=no;TrustServerCertificate=yes
```

SQL Server 2025 (RTM-GDR) 17.0.1135.8 Enterprise on Windows Server 2025, SQL authentication. Credentials come from `DEMO_SQL_USER` and `DEMO_SQL_PASSWORD`.

## Proof

Every included sample must:

- accept the exact same `SQL_CONNECTION_STRING` value as its first command-line argument
- pass that value to the driver unchanged, apart from additions made visibly at the call site
- execute `SELECT TOP (5) ProductID, Name FROM SalesLT.Product ORDER BY ProductID`
- print its driver name, version, and the ordered rows as a table

`run-demo.ps1` does not print the connection string and does not compare rows. Comparison is manual.

## Included

- Microsoft.Data.SqlClient 7.1.0, C#
- go-mssqldb v1.11.2, Go, first release carrying the `yes`/`no` fix from #468
- Microsoft ODBC Driver, C++ calling `SQLDriverConnectW` directly, appends `;Driver={ODBC Driver 18 for SQL Server}` at the call site
- mssql-python 1.15.0, Python

## Excluded

- JDBC 13.6.0: `uid` is a synonym, `pwd` is not, so the password is silently dropped. `trustServerCertificate` takes only `true`/`false`.
- PHP pdo_sqlsrv 5.13.3: rejects `UID`, `PWD`, `User ID`, and `Password` in the DSN. Credentials must be separate constructor arguments.
- mssql-django 2.0.0: requires a structured settings dictionary.

## Open

None.

## Change Control

Expected result: every included driver receives the same unchanged environment value and returns the same five `SalesLT.Product` rows in `ProductID` order.

Stop conditions:

- `SalesLT.Product` is unavailable in the target database.
- A driver requires any connection-string parsing, rewriting, or translation.
- Any driver returns a different value, type, order, or row count.

No database objects or data will be modified. No credential or bearer token will be written to disk or standard output.

Package restores must use the approved package feed proxy for NuGet and PyPI.

## Review

ODBC was initially excluded because it rejects `Encrypt=true` and `Authentication=ActiveDirectoryDefault`. Moving from Fabric with Entra auth to a local SQL Server with SQL authentication removed both objections, leaving only the driver-name append.

The remaining blocker was `TrustServerCertificate`. ODBC accepts only `Yes`/`No`; go-mssqldb parsed booleans with `strconv.ParseBool`, which rejects `yes`. That was fixed upstream in microsoft/go-mssqldb#468 and released in v1.11.2.
