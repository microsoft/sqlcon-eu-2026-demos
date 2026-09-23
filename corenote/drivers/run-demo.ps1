#requires -Version 7
$ErrorActionPreference = 'Stop'

if (-not $env:DEMO_SQL_USER -or -not $env:DEMO_SQL_PASSWORD) {
    throw 'Set DEMO_SQL_USER and DEMO_SQL_PASSWORD before running this script.'
}

$env:SQL_CONNECTION_STRING = "Server=0.0.0.0;Database=AdventureWorksLT;UID=$($env:DEMO_SQL_USER);PWD=$($env:DEMO_SQL_PASSWORD);Encrypt=no;TrustServerCertificate=yes"

# Passed as an argument so the demo shows one string reaching every client. That
# puts the password in each process command line, where any local user can read
# it, so this is a throwaway login and not a pattern to copy.
& "$PSScriptRoot\artifacts\sqlclient\SqlClientDemo.exe" $env:SQL_CONNECTION_STRING
& "$PSScriptRoot\artifacts\go\go-mssqldb.exe" $env:SQL_CONNECTION_STRING
& "$PSScriptRoot\artifacts\odbc\OdbcDemo.exe" "$($env:SQL_CONNECTION_STRING);Driver={ODBC Driver 18 for SQL Server}"
& "$PSScriptRoot\artifacts\mssql-python\mssql-python.exe" $env:SQL_CONNECTION_STRING
