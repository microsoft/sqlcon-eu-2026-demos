[CmdletBinding()]
param(
    [switch]$InitializeDatabase,
    [switch]$TestFoundryAi,
    [switch]$LocalWindowsRuntime,
    [string]$ServerInstance = 'localhost',
    [string]$KubeconfigPath = 'C:\setup\SJ-SQLAI-admin.kubeconfig',
    [string]$DeploymentName = 'phi-35-mini',
    [string]$FoundryNamespace = 'foundry-local-operator',
    [string]$ExternalIPAddress = '172.25.29.251'
)

$ErrorActionPreference = 'Stop'
$databaseName = 'CaldovaRegionalCare'
$sqlcmd = Get-Command sqlcmd -ErrorAction SilentlyContinue

if (-not $sqlcmd) {
    throw 'sqlcmd was not found. Install it from https://learn.microsoft.com/sql/tools/sqlcmd/sqlcmd-download-install and reopen PowerShell.'
}

function Invoke-CaldovaSqlScript {
    param([Parameter(Mandatory)][string]$Name)

    $path = Join-Path $PSScriptRoot $Name
    Write-Host "Running $Name..." -ForegroundColor Cyan
    & $sqlcmd.Source -S $ServerInstance -d master -E -C -b -i $path
    if ($LASTEXITCODE -ne 0) {
        throw "Database script failed: $Name"
    }
}

function New-CaldovaSqlConnection {
    $builder = [Data.SqlClient.SqlConnectionStringBuilder]::new()
    $builder['Data Source'] = $ServerInstance
    $builder['Initial Catalog'] = $databaseName
    $builder['Integrated Security'] = $true
    $builder['Encrypt'] = $true
    $builder['TrustServerCertificate'] = $true
    $builder['Application Name'] = 'Caldova database setup'
    return [Data.SqlClient.SqlConnection]::new($builder.ConnectionString)
}

function Invoke-SqlNonQuery {
    param(
        [Parameter(Mandatory)][Data.SqlClient.SqlConnection]$Connection,
        [Parameter(Mandatory)][string]$CommandText,
        [hashtable]$Parameters = @{}
    )

    $command = $Connection.CreateCommand()
    try {
        $command.CommandText = $CommandText
        foreach ($parameterName in $Parameters.Keys) {
            [void]$command.Parameters.AddWithValue($parameterName, $Parameters[$parameterName])
        }
        [void]$command.ExecuteNonQuery()
    }
    finally {
        $command.Dispose()
    }
}

function Set-AzureLocalGatewayEndpoint {
    foreach ($commandName in 'kubectl', 'curl.exe') {
        if (-not (Get-Command $commandName -ErrorAction SilentlyContinue)) {
            throw "Required command '$commandName' was not found. Run C:\setup\Setup.ps1 first."
        }
    }
    if (-not (Test-Path -LiteralPath $KubeconfigPath -PathType Leaf)) {
        throw "The admin kubeconfig was not found at '$KubeconfigPath'."
    }

    Write-Host "Reading ModelDeployment '$DeploymentName'..." -ForegroundColor Cyan
    $deploymentJson = & kubectl `
        --kubeconfig $KubeconfigPath `
        get modeldeployments.foundrylocal.azure.com $DeploymentName `
        --namespace $FoundryNamespace `
        --request-timeout=15s `
        --output json
    if ($LASTEXITCODE -ne 0 -or -not $deploymentJson) {
        throw "Unable to read ModelDeployment '$DeploymentName'."
    }
    $deployment = $deploymentJson | ConvertFrom-Json
    if ($deployment.status.state -ne 'Running' -or $deployment.status.deploymentReady -ne $true) {
        throw "ModelDeployment '$DeploymentName' is not running and ready."
    }
    $modelId = '{0}:{1}' -f (
        $deployment.spec.model.catalog.name,
        $deployment.spec.model.catalog.version
    )

    $encodedApiKey = & kubectl `
        --kubeconfig $KubeconfigPath `
        get secret "$DeploymentName-api-keys" `
        --namespace $FoundryNamespace `
        --request-timeout=15s `
        --output 'jsonpath={.data.primary-key}'
    if ($LASTEXITCODE -ne 0 -or -not $encodedApiKey) {
        throw "Unable to retrieve the primary API key for '$DeploymentName'."
    }
    $apiKey = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($encodedApiKey))
    $credentialUrl = "https://$ExternalIPAddress/$DeploymentName"

    Write-Host "Validating trusted HTTPS at '$credentialUrl'..." -ForegroundColor Cyan
    & curl.exe `
        --silent `
        --show-error `
        --fail-with-body `
        --ssl-revoke-best-effort `
        --connect-timeout 10 `
        --max-time 30 `
        --header "api-key: $apiKey" `
        "$credentialUrl/v1/model" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Trusted HTTPS validation failed. Run C:\setup\Setup.ps1 from an elevated PowerShell window.'
    }

    $connection = New-CaldovaSqlConnection
    try {
        $connection.Open()

        $masterKeyBytes = [byte[]]::new(48)
        $randomNumberGenerator = [Security.Cryptography.RandomNumberGenerator]::Create()
        try {
            $randomNumberGenerator.GetBytes($masterKeyBytes)
        }
        finally {
            $randomNumberGenerator.Dispose()
        }
        $masterKeyPassword = [Convert]::ToBase64String($masterKeyBytes) + '!aA1'

        Invoke-SqlNonQuery -Connection $connection -CommandText @'
IF NOT EXISTS (
    SELECT 1 FROM sys.symmetric_keys
    WHERE [name] = N'##MS_DatabaseMasterKey##'
)
BEGIN
    DECLARE @Sql nvarchar(max) =
        N'CREATE MASTER KEY ENCRYPTION BY PASSWORD = N''' +
        REPLACE(@MasterKeyPassword, N'''', N'''''') + N''';';
    EXEC sys.sp_executesql @Sql;
END;
'@ -Parameters @{ '@MasterKeyPassword' = $masterKeyPassword }

        Invoke-SqlNonQuery -Connection $connection -CommandText @'
DECLARE @Secret nvarchar(max) =
    N'{"api-key":"' + STRING_ESCAPE(@ApiKey, 'json') + N'"}';
DECLARE @Sql nvarchar(max) =
    N'IF EXISTS (SELECT 1 FROM sys.database_scoped_credentials WHERE [name] = N''' +
    REPLACE(@CredentialUrl, N'''', N'''''') + N''')
        DROP DATABASE SCOPED CREDENTIAL ' + QUOTENAME(@CredentialUrl) + N';
      CREATE DATABASE SCOPED CREDENTIAL ' + QUOTENAME(@CredentialUrl) + N'
      WITH IDENTITY = ''HTTPEndpointHeaders'', SECRET = N''' +
    REPLACE(@Secret, N'''', N'''''') + N''';';
EXEC sys.sp_executesql @Sql;

IF EXISTS (SELECT 1 FROM ai.ModelEndpoint WHERE EndpointName = N'FoundryLocalWindows')
   AND NOT EXISTS (SELECT 1 FROM ai.ModelEndpoint WHERE EndpointName = N'FoundryLocalOnAzureLocal')
    UPDATE ai.ModelEndpoint
    SET EndpointName = N'FoundryLocalOnAzureLocal'
    WHERE EndpointName = N'FoundryLocalWindows';

IF EXISTS (SELECT 1 FROM ai.ModelEndpoint WHERE EndpointName = N'FoundryLocalOnAzureLocal')
    UPDATE ai.ModelEndpoint
    SET BaseUrl = @CredentialUrl,
        ModelId = @ModelId,
        CredentialName = @CredentialUrl,
        TimeoutSeconds = 180,
        IsActive = 1
    WHERE EndpointName = N'FoundryLocalOnAzureLocal';
ELSE
    INSERT ai.ModelEndpoint
        (EndpointName, BaseUrl, ModelId, CredentialName, TimeoutSeconds, IsActive)
    VALUES
        (N'FoundryLocalOnAzureLocal', @CredentialUrl, @ModelId, @CredentialUrl, 180, 1);
'@ -Parameters @{
            '@ApiKey'        = $apiKey
            '@CredentialUrl' = $credentialUrl
            '@ModelId'       = $modelId
        }

        Write-Host "Configured Azure Local Gateway model '$modelId'." -ForegroundColor Green
    }
    finally {
        if ($connection) {
            $connection.Dispose()
        }
        $apiKey = $null
        $encodedApiKey = $null
        $masterKeyPassword = $null
        $masterKeyBytes = $null
    }
}

if ($InitializeDatabase) {
    & $sqlcmd.Source -S $ServerInstance -d master -E -C -b -Q "IF DB_ID(N'$databaseName') IS NOT NULL THROW 50000, '$databaseName already exists. Initialization refused.', 1;"
    if ($LASTEXITCODE -ne 0) {
        throw "Initialization requires an absent $databaseName database. Existing data was not changed."
    }

    '00-create-database.sql',
    '01-schema.sql',
    '02-seed.sql' | ForEach-Object { Invoke-CaldovaSqlScript -Name $_ }
}
else {
    & $sqlcmd.Source -S $ServerInstance -d master -E -C -b -Q "IF DB_ID(N'$databaseName') IS NULL THROW 50000, '$databaseName does not exist. Use -InitializeDatabase.', 1;"
    if ($LASTEXITCODE -ne 0) {
        throw "$databaseName is missing. Run this script with -InitializeDatabase."
    }
}

'02a-native-json-upgrade.sql',
'03-programmability.sql',
'04-test-packet.sql' | ForEach-Object { Invoke-CaldovaSqlScript -Name $_ }

if ($LocalWindowsRuntime) {
    Invoke-CaldovaSqlScript -Name '05-configure-local-model.sql'
}
else {
    Set-AzureLocalGatewayEndpoint
}

Invoke-CaldovaSqlScript -Name '06-skill-invocation.sql'

if ($TestFoundryAi) {
    Invoke-CaldovaSqlScript -Name '07-test-foundry-ai.sql'
    Write-Host 'Database setup and live Foundry Local test passed.' -ForegroundColor Green
}
else {
    Write-Host 'Database setup passed. Use -TestFoundryAi to run 07-test-foundry-ai.sql.' -ForegroundColor Green
}