$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$artifacts = Join-Path $root 'artifacts'
$runtime = 'win-arm64'
$env:PIP_CONFIG_FILE = Join-Path $root 'pip.ini'

if (Test-Path $artifacts) {
    Remove-Item $artifacts -Recurse -Force
}
New-Item $artifacts -ItemType Directory | Out-Null

dotnet restore "$root\sqlclient\SqlClientDemo.csproj" -r $runtime --configfile "$root\NuGet.Config"
if ($LASTEXITCODE -ne 0) { throw 'SqlClient restore failed.' }

dotnet publish "$root\sqlclient\SqlClientDemo.csproj" -c Release -r $runtime --self-contained false --no-restore -o "$artifacts\sqlclient"
if ($LASTEXITCODE -ne 0) { throw 'SqlClient build failed.' }

$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$vsPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.ARM64 -property installationPath
if (-not $vsPath) { throw 'MSVC ARM64 toolset not found.' }
$vcvars = Join-Path $vsPath 'VC\Auxiliary\Build\vcvarsall.bat'

New-Item "$artifacts\odbc" -ItemType Directory | Out-Null
Push-Location "$artifacts\odbc"
try {
    cmd /c "`"$vcvars`" arm64 && cl /nologo /EHsc /W4 /std:c++17 `"$root\odbc\odbc_demo.cpp`" /FeOdbcDemo.exe odbc32.lib"
    if ($LASTEXITCODE -ne 0) { throw 'ODBC build failed.' }
    Remove-Item *.obj
}
finally {
    Pop-Location
}

Push-Location "$root\go"
try {
    go build -o "$artifacts\go\go-mssqldb.exe" .
    if ($LASTEXITCODE -ne 0) { throw 'go-mssqldb build failed.' }
}
finally {
    Pop-Location
}

$python = "$root\.venv\Scripts\python.exe"

# ddbc_bindings.cp314-amd64.pyd is not a legal module name, so PyInstaller does not
# see it as an extension module and --collect-all skips it. mssql_python_odbc is
# reached through importlib.import_module, so it needs collecting by name too.
$sitePackages = "$root\.venv\Lib\site-packages\mssql_python"
& $python -m PyInstaller --noconfirm --clean --onedir --name mssql-python --distpath $artifacts --workpath "$artifacts\pyinstaller-work\mssql-python" --specpath "$artifacts\pyinstaller-spec" --copy-metadata mssql-python --collect-all mssql_python --collect-all mssql_python_odbc --add-binary "$sitePackages\*.pyd;mssql_python" --add-binary "$sitePackages\*.dll;mssql_python" "$root\python\mssql_python_demo.py"
if ($LASTEXITCODE -ne 0) { throw 'mssql-python build failed.' }

Write-Host 'Built four clients under artifacts: SqlClient, go-mssqldb, ODBC, mssql-python.'