@description('Globally unique prefix for resource names.')
param prefix string = 'nandiyo'

param location string = resourceGroup().location

@description('Microsoft Entra login configured as the Azure SQL administrator.')
param entraAdminLogin string

@description('Object ID of the Microsoft Entra user configured as the Azure SQL administrator.')
param entraAdminObjectId string

@description('Create Operations in Bicep. Leave false when a BACPAC import will create it.')
param createDatabase bool = false

@secure()
@description('Optional public client IP for the local BACPAC import. Remove its firewall rule after migration.')
param clientIpAddress string = ''

var suffix = uniqueString(subscription().subscriptionId, resourceGroup().id)
var sqlServerName = '${prefix}-sql-${suffix}'
var webAppName = '${prefix}-web-${suffix}'
var databaseName = 'Operations'

resource sqlServer 'Microsoft.Sql/servers@2023-08-01-preview' = {
  name: sqlServerName
  location: location
  properties: {
    administrators: {
      administratorType: 'ActiveDirectory'
      principalType: 'User'
      login: entraAdminLogin
      sid: entraAdminObjectId
      tenantId: subscription().tenantId
      azureADOnlyAuthentication: true
    }
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
  }
}

resource allowAzureServices 'Microsoft.Sql/servers/firewallRules@2023-08-01-preview' = {
  parent: sqlServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource allowMigrationClient 'Microsoft.Sql/servers/firewallRules@2023-08-01-preview' = if (!empty(clientIpAddress)) {
  parent: sqlServer
  name: 'AllowMigrationClient'
  properties: {
    startIpAddress: clientIpAddress
    endIpAddress: clientIpAddress
  }
}

resource database 'Microsoft.Sql/servers/databases@2023-08-01-preview' = if (createDatabase) {
  parent: sqlServer
  name: databaseName
  location: location
  sku: {
    name: 'HS_Gen5'
    tier: 'Hyperscale'
    family: 'Gen5'
    capacity: 2
  }
  properties: {
    zoneRedundant: false
    readScale: 'Disabled'
  }
}

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: '${prefix}-plan'
  location: location
  sku: {
    name: 'P1v3'
    tier: 'PremiumV3'
  }
  properties: {
    reserved: true
  }
  kind: 'linux'
}

resource webApp 'Microsoft.Web/sites@2023-12-01' = {
  name: webAppName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOTNETCORE|8.0'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      alwaysOn: true
      healthCheckPath: '/health'
      appSettings: [
        {
          name: 'ASPNETCORE_ENVIRONMENT'
          value: 'Production'
        }
      ]
      connectionStrings: [
        {
          name: 'OperationsDatabase'
          connectionString: 'Server=tcp:${sqlServer.properties.fullyQualifiedDomainName},1433;Initial Catalog=${databaseName};Authentication=Active Directory Managed Identity;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;'
          type: 'SQLAzure'
        }
      ]
    }
  }
}

output appUrl string = 'https://${webApp.properties.defaultHostName}'
output webAppName string = webApp.name
output webAppPrincipalId string = webApp.identity.principalId
output sqlServerName string = sqlServer.name
output sqlServerFqdn string = sqlServer.properties.fullyQualifiedDomainName
output databaseName string = databaseName