# One Connection String to Rule Them All

Materials for the corenote drivers segment.

One connection string, assigned once to an environment variable, handed unchanged to four SQL clients that all return the same rows.

```text
Server=0.0.0.0;Database=AdventureWorksLT;UID=<user>;PWD=<password>;Encrypt=no;TrustServerCertificate=yes
```

Each client takes that string as its first command-line argument, runs `SELECT TOP (5) ProductID, Name FROM SalesLT.Product ORDER BY ProductID`, and prints its driver name, version, and the rows.

## Before you start

| Needed for | Tool |
|---|---|
| `run-demo.ps1` | PowerShell 7 |
| C# client | .NET 10 SDK |
| C++ ODBC client | Visual Studio Build Tools, MSVC ARM64 toolset |
| C++ ODBC client | Microsoft ODBC Driver 18 for SQL Server |
| Go client | Go 1.25 or later |
| Python client | Python 3.14 |

The build shells out to `vcvarsall.bat arm64`, so the MSVC C++ workload has to be installed or the ODBC client will not compile.

You also need network access to the SQL Server named in the string, and a login with read access to `SalesLT.Product` in `AdventureWorksLT`.

## Setup

Create the virtual environment first. The build script uses `.venv\Scripts\python.exe`, so it fails if this has not been run.

```powershell
python -m venv .venv
$env:PIP_CONFIG_FILE = "$PWD\pip.ini"
.\.venv\Scripts\python.exe -m pip install -r .\python\requirements.txt
```

NuGet and PyPI go through the package feed proxy configured by `NuGet.Config` and `pip.ini`. Set `PIP_CONFIG_FILE` as shown, because pip on Windows does not pick up a repository-level config file on its own.

## Build

```powershell
.\build-demo.ps1
```

This wipes `artifacts\` and rebuilds all four clients into it. It prints one line when it finishes:

```text
Built four clients under artifacts: SqlClient, go-mssqldb, ODBC, mssql-python.
```

## Run

```powershell
$env:DEMO_SQL_USER = '<user>'
$env:DEMO_SQL_PASSWORD = '<password>'
.\run-demo.ps1
```

Credentials come from those two variables so no password is stored in the repo. The script assembles the connection string, assigns it to `SQL_CONNECTION_STRING`, and passes that one value to each client in turn.

## What you should see

Four blocks, one per client, differing only in the first line:

```text
SqlClient 7.1.0
Product ID  Name
----------  ----
680         HL Road Frame - Black, 58
706         HL Road Frame - Red, 58
707         Sport-100 Helmet, Red
708         Sport-100 Helmet, Black
709         Mountain Bike Socks, M

go-mssqldb v1.11.2
...
ODBC 18.7.1
...
mssql-python 1.15.0
...
```

The script does not compare the rows. Check them by eye, or send the output to a file and diff it.

Driver versions are read at runtime rather than hardcoded, so they track whatever you have installed.

## Using a different server

The server and database are hardcoded in `run-demo.ps1`:

```powershell
$env:SQL_CONNECTION_STRING = "Server=0.0.0.0;Database=AdventureWorksLT;..."
```

Edit that line to point somewhere else. Leave `Encrypt=no;TrustServerCertificate=yes` spelled as it is, or read "Why these four" first, because those spellings are the point of the demo.

## If something fails

- **`Set DEMO_SQL_USER and DEMO_SQL_PASSWORD before running this script.`** Neither variable is set in the current shell. They do not persist between terminal sessions.
- **`MSVC ARM64 toolset not found.`** `build-demo.ps1` could not locate the C++ ARM64 toolset through `vswhere`. Install the C++ build tools workload.
- **`pip install` cannot reach the index.** `PIP_CONFIG_FILE` is not set, so pip is not reading `pip.ini`.
- **One client fails and the other three succeed.** That driver disagrees with the string, which is the failure this demo exists to show. Read the error carefully: a driver may reject a keyword outright, or ignore it and fail later as something else, which is how the JDBC case below behaves.

## Clients

| Client | Language | Version |
|---|---|---:|
| Microsoft.Data.SqlClient | C# | 7.1.0 |
| go-mssqldb | Go | 1.11.2 |
| Microsoft ODBC Driver | C++ | reported at runtime via `SQL_DRIVER_VER` |
| mssql-python | Python | 1.15.0 |

The ODBC client calls `SQLDriverConnectW` directly, so the string reaches the driver manager with nothing in between.

Only one client modifies the string, and it does so visibly at the call site in `run-demo.ps1`:

- ODBC appends `;Driver={ODBC Driver 18 for SQL Server}`. ODBC needs a driver name and the string carries none.

Nothing else is added, removed, reordered, or reparsed.

## Why these four

`TrustServerCertificate` had no value that every Microsoft SQL driver accepted:

| Value | go-mssqldb | ODBC 18 | SqlClient | mssql-python |
|---|---|---|---|---|
| `yes` | rejected until #468 | accepted | accepted | accepted |
| `true` | accepted | rejected | accepted | rejected |
| `1` | accepted | rejected | rejected | rejected |

ODBC accepts only `Yes`/`No`, so `yes` was the only candidate. `go-mssqldb` rejected it until [microsoft/go-mssqldb#468](https://github.com/microsoft/go-mssqldb/pull/468), which shipped in v1.11.2. That is the version `go/go.mod` pins, and that fix is what made a single shared string possible.

## Excluded, and why

Each of these needs the string taken apart rather than added to.

- **JDBC.** `uid` is an accepted synonym but `pwd` is not, so the password is silently dropped and login fails as `Login failed for user`. `trustServerCertificate` also accepts only `true`/`false`. Source in `jdbc/` is kept as a record; `build-demo.ps1` does not build it.
- **PHP.** `pdo_sqlsrv` 5.13.3 rejects every credential keyword in the DSN, including `UID`, `PWD`, `User ID`, and `Password`. Credentials must be separate `PDO::__construct` arguments. Everything else in the string, including `Encrypt=no` and `TrustServerCertificate=yes`, is accepted.
- **mssql-django.** Requires the fields split into a structured settings dictionary.
