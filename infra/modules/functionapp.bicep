@description('Azure region for all resources')
param location string

@description('Resource tags')
param tags object

@description('Base name used to derive resource names')
param baseName string

@description('Name of the host storage account for Functions runtime')
param hostStorageAccountName string

@description('Application Insights connection string')
param appInsightsConnectionString string

@description('Name of the dedicated data storage account')
param dataStorageAccountName string

@description('Key Vault URI for Key Vault references')
param keyVaultUri string

// ---------------------------------------------------------------------------
// Shared app settings applied to both the production and staging slots.
// Any new setting added here is automatically inherited by the staging slot,
// ensuring parity without manual synchronisation (acceptance criterion #4).
// ---------------------------------------------------------------------------

var commonAppSettings = [
  {
    name: 'FUNCTIONS_EXTENSION_VERSION'
    value: '~4'
  }
  {
    name: 'FUNCTIONS_WORKER_RUNTIME'
    value: 'python'
  }
  {
    name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
    value: appInsightsConnectionString
  }
  {
    name: 'AzureWebJobsStorage__accountName'
    value: hostStorageAccountName
  }
  {
    name: 'AzureWebJobsStorage__blobServiceUri'
    value: 'https://${hostStorageAccountName}.blob.${environment().suffixes.storage}'
  }
  {
    name: 'AzureWebJobsStorage__queueServiceUri'
    value: 'https://${hostStorageAccountName}.queue.${environment().suffixes.storage}'
  }
  {
    name: 'AzureWebJobsStorage__tableServiceUri'
    value: 'https://${hostStorageAccountName}.table.${environment().suffixes.storage}'
  }
  {
    name: 'DATA_STORAGE_ACCOUNT_NAME'
    value: dataStorageAccountName
  }
  {
    name: 'TRAPI_ENDPOINT'
    value: '@Microsoft.KeyVault(SecretUri=${keyVaultUri}secrets/trapiEndpoint/)'
  }
  {
    name: 'TRAPI_DEPLOYMENT_NAME'
    value: '@Microsoft.KeyVault(SecretUri=${keyVaultUri}secrets/trapiDeploymentName/)'
  }
  {
    name: 'WEBSITE_RUN_FROM_PACKAGE'
    value: '1'
  }
]

// ---------------------------------------------------------------------------
// Consumption App Service Plan (Linux)
// Note: Azure Functions Consumption (Y1/Dynamic) supports up to one additional
// deployment slot (staging) in addition to the production slot.  Slot swap
// behaviour differs from Premium/Dedicated — there is no pre-warmed instance,
// so cold-start latency is expected during pre-swap smoke tests.
// ---------------------------------------------------------------------------

resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: 'asp-${baseName}'
  location: location
  tags: tags
  kind: 'functionapp'
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true
  }
}

// ---------------------------------------------------------------------------
// Function App (Python 3.11, system-assigned MI, identity-based storage)
// ---------------------------------------------------------------------------

resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: 'fn-${baseName}'
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    reserved: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      appSettings: commonAppSettings
    }
    httpsOnly: true
  }
}

// ---------------------------------------------------------------------------
// Staging deployment slot (same settings as production; WEBSITE_SLOT_NAME is
// marked slot-sticky so it does not travel to production on slot swap)
// ---------------------------------------------------------------------------

resource stagingSlot 'Microsoft.Web/sites/slots@2023-01-01' = {
  name: 'staging'
  parent: functionApp
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    reserved: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      appSettings: concat(commonAppSettings, [
        {
          name: 'WEBSITE_SLOT_NAME'
          value: 'staging'
        }
      ])
    }
    httpsOnly: true
  }
}

// Mark WEBSITE_SLOT_NAME and WEBSITE_RUN_FROM_PACKAGE as slot-sticky so they
// are not carried to production during a slot swap.  This list is authoritative
// — any future sticky settings must be added here.
resource slotConfigNames 'Microsoft.Web/sites/config@2023-01-01' = {
  name: 'slotConfigNames'
  parent: functionApp
  dependsOn: [stagingSlot]
  properties: {
    appSettingNames: ['WEBSITE_SLOT_NAME', 'WEBSITE_RUN_FROM_PACKAGE']
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------

output functionAppName string = functionApp.name
output functionPrincipalId string = functionApp.identity.principalId
output stagingSlotPrincipalId string = stagingSlot.identity.principalId
