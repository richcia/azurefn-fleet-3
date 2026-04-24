@description('Azure region for all resources. Defaults to resource group location.')
param location string = resourceGroup().location

@description('TRAPI endpoint URL (stored in Key Vault)')
@secure()
param trapiEndpoint string

@description('TRAPI GPT-4o deployment name (stored in Key Vault)')
@secure()
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
    trapiDeploymentName: trapiDeploymentName
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
    hostStorageAccountName: storage.outputs.hostStorageAccountName
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    dataStorageAccountName: storage.outputs.dataStorageAccountName
    keyVaultUri: keyvault.outputs.keyVaultUri
  }
}

// ---------------------------------------------------------------------------
// RBAC role assignments
// ---------------------------------------------------------------------------

module rbac 'modules/rbac.bicep' = {
  name: 'rbac'
  params: {
    functionPrincipalId: functionapp.outputs.functionPrincipalId
    stagingSlotPrincipalId: functionapp.outputs.stagingSlotPrincipalId
    dataStorageAccountName: storage.outputs.dataStorageAccountName
    dataContainerName: dataContainerName
    hostStorageAccountName: storage.outputs.hostStorageAccountName
    keyVaultName: keyvault.outputs.keyVaultName
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
output stagingSlotPrincipalId string = functionapp.outputs.stagingSlotPrincipalId
output dataStorageAccountName string = storage.outputs.dataStorageAccountName
output hostStorageAccountName string = storage.outputs.hostStorageAccountName
output keyVaultName string = keyvault.outputs.keyVaultName
output dataContainerResourceId string = storage.outputs.dataContainerResourceId
output appInsightsId string = monitoring.outputs.appInsightsId
