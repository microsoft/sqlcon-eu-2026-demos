#!/bin/zsh
set -euo pipefail

root="${0:A:h}"
database="${DEMO_SQL_DATABASE:-AdventureWorksLT}"
port="${DEMO_SQL_PORT:-1433}"
trust_server_certificate="${DEMO_SQL_TRUST_SERVER_CERTIFICATE:-no}"

[[ -n "${DEMO_SQL_SERVER:-}" ]] || {
    print -u2 "Set DEMO_SQL_SERVER before running this script."
    exit 1
}
[[ -n "${DEMO_SQL_USER:-}" ]] || {
    print -u2 "Set DEMO_SQL_USER before running this script."
    exit 1
}
if [[ -z "${DEMO_SQL_PASSWORD:-}" ]]; then
    read -rs "DEMO_SQL_PASSWORD?SQL password: "
    print
fi
[[ -n "$DEMO_SQL_PASSWORD" ]] || {
    print -u2 "SQL password cannot be empty."
    exit 1
}
[[ "$DEMO_SQL_USER" != *';'* && "$DEMO_SQL_PASSWORD" != *';'* ]] || {
    print -u2 "DEMO_SQL_USER and DEMO_SQL_PASSWORD cannot contain semicolons."
    exit 1
}
[[ "$port" == <1-65535> ]] || {
    print -u2 "DEMO_SQL_PORT must be between 1 and 65535."
    exit 1
}
[[ "$trust_server_certificate" == yes || "$trust_server_certificate" == no ]] || {
    print -u2 "DEMO_SQL_TRUST_SERVER_CERTIFICATE must be yes or no."
    exit 1
}
[[ -f "$root/artifacts/sqlclient/SqlClientDemo.dll" ]] || {
    print -u2 "Build artifacts are missing. Run ./build-demo.sh first."
    exit 1
}

dotnet="$(brew --prefix dotnet)/libexec/dotnet"
[[ -x "$dotnet" ]] || {
    print -u2 "Homebrew .NET 10 SDK is missing. Run ./build-demo.sh after installing it."
    exit 1
}

connection_string="Server=$DEMO_SQL_SERVER,$port;Database=$database;Encrypt=yes;TrustServerCertificate=$trust_server_certificate;UID=$DEMO_SQL_USER;PWD=$DEMO_SQL_PASSWORD"
display_connection_string="Server=$DEMO_SQL_SERVER,$port;Database=$database;Encrypt=yes;TrustServerCertificate=$trust_server_certificate;UID=$DEMO_SQL_USER;PWD=********"

temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/sql-driver-demo.XXXXXX")"
trap 'rm -rf "$temp_dir"' EXIT
baseline_rows=""

run_client() {
    local key="$1"
    local label="$2"
    shift 2

    local output="$temp_dir/$key.txt"
    local rows="$temp_dir/$key.rows"
    printf "  %-24s" "$label"

    if ! "$@" >"$output" 2>&1; then
        print "[FAIL]"
        print -u2 "$label could not complete:"
        DEMO_ERROR_FILE="$output" DEMO_SQL_PASSWORD="$DEMO_SQL_PASSWORD" \
            "$root/.venv/bin/python" -c \
            'import os, pathlib; print(pathlib.Path(os.environ["DEMO_ERROR_FILE"]).read_text().replace(os.environ["DEMO_SQL_PASSWORD"], "********"), end="")' \
            >&2
        return 1
    fi

    sed -n '4,8p' "$output" >"$rows"
    if [[ "$(wc -l <"$rows" | tr -d ' ')" != "5" ]]; then
        print "[FAIL]"
        print -u2 "$label did not return exactly five rows."
        return 1
    fi

    if [[ -z "$baseline_rows" ]]; then
        baseline_rows="$rows"
    elif ! cmp -s "$baseline_rows" "$rows"; then
        print "[FAIL]"
        print -u2 "$label returned different rows."
        return 1
    fi

    print "[PASS] $(sed -n '1p' "$output")"
}

print
print "ONE CONNECTION STRING | FOUR DRIVERS | SAME RESULT"
print "Target: $DEMO_SQL_SERVER / $database"
print "Shared connection string:"
print -r -- "$display_connection_string"
print "Auth: SQL authentication"
print

run_client sqlclient "C#" env SQL_CONNECTION_STRING="$connection_string" \
    "$dotnet" "$root/artifacts/sqlclient/SqlClientDemo.dll"
run_client go "Go" env SQL_CONNECTION_STRING="$connection_string" \
    "$root/artifacts/go/go-mssqldb"
run_client python "Python" env SQL_CONNECTION_STRING="$connection_string" \
    "$root/.venv/bin/python" "$root/python/mssql_python_demo.py"
run_client odbc "C++" env SQL_CONNECTION_STRING="$connection_string;Driver={ODBC Driver 18 for SQL Server}" \
    "$root/artifacts/odbc/OdbcDemo"
printf "  %-24s%s\n" "" 'ODBC requires "Driver={ODBC Driver 18 for SQL Server}"'

fingerprint="$(shasum -a 256 "$baseline_rows" | awk '{print substr($1, 1, 12)}')"

print
print "SHARED QUERY RESULT"
print "Product ID  Name"
print -r -- "----------  ----"
cat "$baseline_rows"
print
print "MATCH CONFIRMED | 5 rows | SHA-256 $fingerprint"