#!/bin/zsh
set -euo pipefail

root="${0:A:h}"
artifacts="$root/artifacts"
runtime="osx-$(uname -m)"

fail() {
    print -u2 "Build failed: $1"
    exit 1
}

for command_name in go python3 clang++ brew; do
    command -v "$command_name" >/dev/null || fail "$command_name is not installed."
done

dotnet_root="$(brew --prefix dotnet)/libexec"
dotnet="$dotnet_root/dotnet"
[[ -x "$dotnet" ]] || fail "Homebrew .NET 10 SDK is not installed."
[[ "$($dotnet --version)" == 10.* ]] || fail ".NET 10 SDK is required."
export DOTNET_ROOT="$dotnet_root"
unixodbc_prefix="$(brew --prefix unixodbc)"
msodbcsql_prefix="$(brew --prefix msodbcsql18)"
rm -rf "$artifacts"
mkdir -p "$artifacts/sqlclient" "$artifacts/go" "$artifacts/odbc"

print "Building Microsoft.Data.SqlClient..."
"$dotnet" restore "$root/sqlclient/SqlClientDemo.csproj" -r "$runtime"
"$dotnet" publish "$root/sqlclient/SqlClientDemo.csproj" -c Release -r "$runtime" \
    --self-contained false --no-restore -o "$artifacts/sqlclient"

print "Building Microsoft ODBC Driver client..."
clang++ -std=c++17 -Wall -Wextra -pedantic \
    -I"$unixodbc_prefix/include" -isystem "$msodbcsql_prefix/include/msodbcsql18" \
    "$root/odbc/odbc_demo.cpp" \
    -L"$unixodbc_prefix/lib" -lodbc -o "$artifacts/odbc/OdbcDemo"

print "Building go-mssqldb..."
(
    cd "$root/go"
    go build -o "$artifacts/go/go-mssqldb" .
)

print "Preparing mssql-python..."
[[ -x "$root/.venv/bin/python" ]] || python3 -m venv "$root/.venv"
"$root/.venv/bin/python" -m pip install \
    --disable-pip-version-check -r "$root/python/requirements.txt"

print
print "Built four clients for $runtime under artifacts/."