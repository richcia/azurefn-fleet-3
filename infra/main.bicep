@description('Deployment location.')
param location string = resourceGroup().location

@description('Existing Function App name to configure with Key Vault references.')
param functionAppName string

@description('Principal ID of the Function App system-assigned managed identity (validated deployment input).')
param functionAppPrincipalId string

@description('Name of the Key Vault to create.')
param keyVaultName string = 'kv${uniqueString(resourceGroup().id)}'

@description('Name of the storage account that hosts the roster container.')
param dataStorageAccountName string

@description('Name of the Log Analytics workspace to create for monitoring.')
param logAnalyticsWorkspaceName string = 'law${uniqueString(resourceGroup().id)}'

@description('Name of the Application Insights component to create.')
param applicationInsightsName string = 'appi${uniqueString(resourceGroup().id)}'

@description('Name of the action group used for alert notifications.')
param actionGroupName string = 'ag-alerts-${uniqueString(resourceGroup().id)}'

@description('Email address used by the alert action group.')
param alertEmailAddress string = 'rciapala@microsoft.com'

@description('Secret name used for fallback TRAPI credentials in Key Vault references.')
param trapiFallbackSecretName string = 'trapi-fallback-credential'

@allowed([
  true
])
@description('Set to true after confirming the selected region supports zone-redundant Key Vault.')
param zoneRedundancyRegionConfirmed bool = true

@description('Resource tags.')
param tags object = {
  project: '1985-NY-Yankees'
  owner: 'rciapala'
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' existing = {
  name: functionAppName
}

var existingAppSettings = list('${functionApp.id}/config/appsettings', '2023-12-01').properties
resource dataStorageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: dataStorageAccountName
}

resource dataStorageBlobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' existing = {
  parent: dataStorageAccount
  name: 'default'
}

resource rosterContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: dataStorageBlobService
  name: 'yankees-roster'
  properties: {
    publicAccess: 'None'
  }
}

module keyVault 'modules/keyvault.bicep' = {
  name: 'keyVaultModule'
  params: {
    keyVaultName: keyVaultName
    location: location
    functionAppPrincipalId: functionAppPrincipalId
    zoneRedundancyRegionConfirmed: zoneRedundancyRegionConfirmed
    tags: tags
  }
}

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoringModule'
  params: {
    location: location
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
    applicationInsightsName: applicationInsightsName
    tags: tags
  }
}

module alerts 'modules/alerts.bicep' = {
  name: 'alertsModule'
  params: {
    location: location
    applicationInsightsResourceId: monitoring.outputs.applicationInsightsId
    applicationInsightsName: monitoring.outputs.applicationInsightsName
    actionGroupName: actionGroupName
    alertEmailAddress: alertEmailAddress
    tags: tags
  }
}

resource functionAppAppSettings 'Microsoft.Web/sites/config@2023-12-01' = {
  name: 'appsettings'
  parent: functionApp
  properties: union(existingAppSettings, {
    KEY_VAULT_URI: keyVault.outputs.keyVaultUri
    TRAPI_FALLBACK_CREDENTIAL: '@Microsoft.KeyVault(SecretUri=${keyVault.outputs.keyVaultUri}secrets/${trapiFallbackSecretName}/)'
    APPLICATIONINSIGHTS_CONNECTION_STRING: monitoring.outputs.applicationInsightsConnectionString
  })
}

output keyVaultId string = keyVault.outputs.keyVaultId
output keyVaultName string = keyVault.outputs.keyVaultName
output keyVaultUri string = keyVault.outputs.keyVaultUri
output applicationInsightsId string = monitoring.outputs.applicationInsightsId
output applicationInsightsName string = monitoring.outputs.applicationInsightsName
output logAnalyticsWorkspaceId string = monitoring.outputs.logAnalyticsWorkspaceId
output actionGroupId string = alerts.outputs.actionGroupId
