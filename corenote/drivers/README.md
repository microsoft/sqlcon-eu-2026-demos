# One Connection String to Rule Them All

This macOS demo passes one SQL-authentication connection string unchanged to four Microsoft SQL drivers, runs the same query, and verifies that every driver returns the same five rows.

| Client | Driver |
|---|---|
| C# | Microsoft.Data.SqlClient 7.1.0 |
| Go | go-mssqldb 1.11.2 |
| Python | mssql-python 1.15.0 |
| C++ | Microsoft ODBC Driver 18 |

All clients receive this value through `SQL_CONNECTION_STRING`:

```text
Server=<server>,<port>;Database=<database>;Encrypt=yes;TrustServerCertificate=<yes-or-no>;UID=<user>;PWD=<password>
```

ODBC has one visible exception: its required `Driver={ODBC Driver 18 for SQL Server}` selector is appended at the call site. No other client parses, translates, or rewrites the string.

## Prerequisites

- macOS on Apple silicon
- [Homebrew](https://brew.sh/)
- .NET 10 SDK
- Go
- Python 3.13 or later
- unixODBC
- Microsoft ODBC Driver 18 for SQL Server
- A reachable SQL Server or Azure SQL database using SQL authentication

Install the build dependencies:

```zsh
brew install dotnet go python@3.13 unixodbc
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
HOMEBREW_ACCEPT_EULA=Y brew install msodbcsql18
```

## Prepare the database

Run [`database/setup.sql`](database/setup.sql) while connected as an administrator. It creates `AdventureWorksLT`, `SalesLT.Product`, and the five deterministic rows only when they are missing.

For a disposable local SQL Server 2025 container, the `SA` login is sufficient for setup and demonstration. For shared environments, use a dedicated login with only `CONNECT` and `SELECT` access to the demo database. Do not use these scripts as a production credential pattern.

## Build

From this directory:

```zsh
chmod +x ./build-demo.sh ./run-demo.sh
./build-demo.sh
```

Build output is written to the ignored `artifacts/` directory. Python dependencies are installed in the ignored `.venv/` directory.

## Run against a local container

This verified example targets SQL Server 2025 at `127.0.0.1:1437`. The runner prompts for the password without echoing it or placing it in shell history:

```zsh
DEMO_SQL_SERVER='127.0.0.1' DEMO_SQL_PORT='1437' DEMO_SQL_DATABASE='AdventureWorksLT' DEMO_SQL_USER='SA' DEMO_SQL_TRUST_SERVER_CERTIFICATE='yes' ./run-demo.sh
```

Use `127.0.0.1` rather than `localhost` for this local setup because mssql-python 1.15.0 does not resolve `localhost` correctly on the tested Mac.

To target another server, change the `DEMO_SQL_*` values. Keep certificate validation enabled for remote servers by omitting `DEMO_SQL_TRUST_SERVER_CERTIFICATE` or setting it to `no`.

## Expected result

```text
  C#                      [PASS] SqlClient 7.1.0
  Go                      [PASS] go-mssqldb v1.11.2
  Python                  [PASS] mssql-python 1.15.0
  C++                     [PASS] ODBC 18.7.1

MATCH CONFIRMED | 5 rows | SHA-256 66e53a0eba12
```

Each client executes:

```sql
SELECT TOP (5) ProductID, Name
FROM SalesLT.Product
ORDER BY ProductID;
```

The runner redacts the password in displayed connection strings and errors, requires exactly five rows, compares every result byte for byte, and prints the fingerprint only after all four clients match.

## Security notes

- The password is read with terminal echo disabled when `DEMO_SQL_PASSWORD` is unset.
- The password is not stored in this repository or passed as a process argument.
- Supplying `DEMO_SQL_PASSWORD` non-interactively is supported for automation, but protect the environment and logs.
- `TrustServerCertificate=yes` is appropriate only for the disposable local container example.
- Build artifacts, virtual environments, logs, and local environment files are ignored.