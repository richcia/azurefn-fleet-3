@description('Azure region for the Function App and its Consumption plan.')
param location string

@description('Name of the Function App (must be globally unique).')
param functionAppName string

@description('Name of the Storage Account used for AzureWebJobsStorage (identity-based).')
param storageAccountName string

@description('TRAPI (Azure OpenAI) endpoint URL.')
param trapiEndpoint string

@description('TRAPI deployment name (model alias).')
param trapiDeploymentName string

@description('TRAPI API version.')
param trapiApiVersion string

@description('Resource tags applied to all resources in this module.')
param tags object = {}

// ---------------------------------------------------------------------------
// Consumption Plan — Linux
// ---------------------------------------------------------------------------

resource consumptionPlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: '${functionAppName}-plan'
  location: location
  tags: tags
  kind: 'linux'
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true // required for Linux
  }
}

// ---------------------------------------------------------------------------
// Function App
// ---------------------------------------------------------------------------

resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: functionAppName
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: consumptionPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appSettings: [
        {
          name: 'AzureWebJobsStorage__accountName'
          value: storageAccountName
        }
        {
          name: 'STORAGE_ACCOUNT_NAME'
          value: storageAccountName
        }
        {
          name: 'TRAPI_ENDPOINT'
          value: trapiEndpoint
        }
        {
          name: 'TRAPI_DEPLOYMENT_NAME'
          value: trapiDeploymentName
        }
        {
          name: 'TRAPI_API_VERSION'
          value: trapiApiVersion
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
      ]
    }
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------

@description('The name of the provisioned Function App.')
output functionAppName string = functionApp.name

@description('The resource ID of the provisioned Function App.')
output functionAppId string = functionApp.id

@description('The principal ID of the system-assigned managed identity.')
output principalId string = functionApp.identity.principalId

@description('The default hostname of the Function App.')
output defaultHostname string = functionApp.properties.defaultHostName
