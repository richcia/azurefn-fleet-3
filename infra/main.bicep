targetScope = 'resourceGroup'

@description('Azure region for all resources. Must support zone-redundant Key Vault.')
@allowed([
  'australiaeast'
  'brazilsouth'
  'canadacentral'
  'centralus'
  'eastus'
  'eastus2'
  'francecentral'
  'japaneast'
  'koreacentral'
  'northeurope'
  'southcentralus'
  'southeastasia'
  'swedencentral'
  'uksouth'
  'westeurope'
  'westus2'
  'westus3'
])
param location string

@description('TRAPI endpoint URL used by the function app.')
param trapiEndpoint string = 'https://example.openai.azure.com'

@description('TRAPI deployment name used by the function app.')
param trapiDeploymentName string = 'gpt-4o'

@description('TRAPI API version used by the function app.')
param trapiApiVersion string = '2024-02-01'

@description('Tags applied to all resources.')
param tags object = {
  project: '1985-NY-Yankees'
  owner: 'rciapala'
}

var suffix = toLower(uniqueString(resourceGroup().id))
var storageAccountName = 'st${take(suffix, 22)}'
var functionAppName = 'func-yankees-${take(suffix, 8)}'
var hostingPlanName = 'plan-yankees-${take(suffix, 8)}'
var logAnalyticsWorkspaceName = 'log-yankees-${take(suffix, 8)}'
var appInsightsName = 'appi-yankees-${take(suffix, 8)}'
var keyVaultName = 'kv${take(suffix, 22)}'

module storage './modules/storage.bicep' = {
  name: 'storageDeployment'
  params: {
    accountName: storageAccountName
    location: location
    tags: tags
  }
}

module monitoring './modules/monitoring.bicep' = {
  name: 'monitoringDeployment'
  params: {
    workspaceName: logAnalyticsWorkspaceName
    appInsightsName: appInsightsName
    location: location
    tags: tags
  }
}

module functionApp './modules/functionapp.bicep' = {
  name: 'functionAppDeployment'
  params: {
    functionAppName: functionAppName
    hostingPlanName: hostingPlanName
    location: location
    storageAccountName: storage.outputs.storageAccountName
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    trapiEndpoint: trapiEndpoint
    trapiDeploymentName: trapiDeploymentName
    trapiApiVersion: trapiApiVersion
    tags: tags
  }
}

module keyVault './modules/keyvault.bicep' = {
  name: 'keyVaultDeployment'
  params: {
    keyVaultName: keyVaultName
    location: location
    tags: tags
  }
}

output storageAccountName string = storage.outputs.storageAccountName
output functionAppName string = functionApp.outputs.functionAppName
output functionAppPrincipalId string = functionApp.outputs.functionAppPrincipalId
output applicationInsightsName string = monitoring.outputs.appInsightsName
output applicationInsightsConnectionString string = monitoring.outputs.appInsightsConnectionString
output logAnalyticsWorkspaceName string = monitoring.outputs.workspaceName
output keyVaultName string = keyVault.outputs.keyVaultName
output keyVaultUri string = keyVault.outputs.keyVaultUri
