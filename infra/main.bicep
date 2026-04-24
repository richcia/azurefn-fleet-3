@description('Azure region for all resources. Defaults to resource group location.')
param location string = resourceGroup().location

@description('TRAPI endpoint URL (stored in Key Vault)')
@secure()
param trapiEndpoint string

@description('TRAPI GPT-4o deployment name (non-sensitive plain setting)')
param trapiDeploymentName string

@description('Email address for operational alerts')
param alertEmailAddress string

// ---------------------------------------------------------------------------
// Shared tags applied to all resources
// ---------------------------------------------------------------------------

var tags = {
  project: '1985-NY-Yankees'
  owner: 'rciapala'
}

// Stable 13-character suffix derived from the resource group; ensures
// globally-unique storage/function names without manual input.
var baseName = uniqueString(resourceGroup().id)

// Single source of truth for the data container name; passed to both
// storage and rbac modules to prevent silent drift between modules.
var dataContainerName = 'yankees-roster'

// ---------------------------------------------------------------------------
// Storage (data account + host account)
// ---------------------------------------------------------------------------

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    location: location
    tags: tags
    dataStorageAccountName: 'data${baseName}'
    hostStorageAccountName: 'host${baseName}'
    dataContainerName: dataContainerName
  }
}

// ---------------------------------------------------------------------------
// Monitoring (Log Analytics Workspace + Application Insights)
// ---------------------------------------------------------------------------

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    tags: tags
    baseName: baseName
  }
}

// ---------------------------------------------------------------------------
// Key Vault (RBAC model; TRAPI secrets stored at deploy time)
// ---------------------------------------------------------------------------

module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  params: {
    location: location
    tags: tags
    baseName: baseName
    trapiEndpoint: trapiEndpoint
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
  }
}

// ---------------------------------------------------------------------------
// Function App (Consumption Plan, Python 3.11, system-assigned MI)
// ---------------------------------------------------------------------------

module functionapp 'modules/functionapp.bicep' = {
  name: 'functionapp'
  params: {
    location: location
    tags: tags
    baseName: baseName
  }
}

// ---------------------------------------------------------------------------
// RBAC role assignments
// ---------------------------------------------------------------------------

module rbac 'modules/rbac.bicep' = {
  name: 'rbac'
  params: {
    functionPrincipalId: functionapp.outputs.functionPrincipalId
    dataStorageAccountName: storage.outputs.dataStorageAccountName
    dataContainerName: dataContainerName
    hostStorageAccountName: storage.outputs.hostStorageAccountName
    keyVaultName: keyvault.outputs.keyVaultName
  }
}

// ---------------------------------------------------------------------------
// Key Vault reference app settings — applied AFTER Key Vault Secrets User
// RBAC assignment completes to prevent 403 errors during KV reference
// resolution at Function App startup.
// ---------------------------------------------------------------------------

resource functionAppRef 'Microsoft.Web/sites@2023-01-01' existing = {
  name: functionapp.outputs.functionAppName
}

resource kvAppsettings 'Microsoft.Web/sites/config@2023-01-01' = {
  name: 'appsettings'
  parent: functionAppRef
  dependsOn: [rbac]
  properties: {
    FUNCTIONS_EXTENSION_VERSION: '~4'
    FUNCTIONS_WORKER_RUNTIME: 'python'
    APPLICATIONINSIGHTS_CONNECTION_STRING: '@Microsoft.KeyVault(SecretUri=${keyvault.outputs.keyVaultUri}secrets/appInsightsConnectionString/)'
    AzureWebJobsStorage__accountName: storage.outputs.hostStorageAccountName
    AzureWebJobsStorage__blobServiceUri: 'https://${storage.outputs.hostStorageAccountName}.blob.${environment().suffixes.storage}'
    AzureWebJobsStorage__queueServiceUri: 'https://${storage.outputs.hostStorageAccountName}.queue.${environment().suffixes.storage}'
    AzureWebJobsStorage__tableServiceUri: 'https://${storage.outputs.hostStorageAccountName}.table.${environment().suffixes.storage}'
    DATA_STORAGE_ACCOUNT_NAME: storage.outputs.dataStorageAccountName
    TRAPI_ENDPOINT: '@Microsoft.KeyVault(SecretUri=${keyvault.outputs.keyVaultUri}secrets/trapiEndpoint/)'
    TRAPI_DEPLOYMENT_NAME: trapiDeploymentName
    WEBSITE_RUN_FROM_PACKAGE: '1'
  }
}

// ---------------------------------------------------------------------------
// Alerts (email action group + exception query alert)
// ---------------------------------------------------------------------------

module alerts 'modules/alerts.bicep' = {
  name: 'alerts'
  params: {
    location: location
    tags: tags
    alertEmailAddress: alertEmailAddress
    appInsightsId: monitoring.outputs.appInsightsId
    functionAppName: functionapp.outputs.functionAppName
  }
}

// ---------------------------------------------------------------------------
// Outputs consumed by cd-infra.yml validation step
// ---------------------------------------------------------------------------

output functionAppName string = functionapp.outputs.functionAppName
output functionPrincipalId string = functionapp.outputs.functionPrincipalId
output dataStorageAccountName string = storage.outputs.dataStorageAccountName
output hostStorageAccountName string = storage.outputs.hostStorageAccountName
output keyVaultName string = keyvault.outputs.keyVaultName
output dataContainerResourceId string = storage.outputs.dataContainerResourceId
output appInsightsId string = monitoring.outputs.appInsightsId
