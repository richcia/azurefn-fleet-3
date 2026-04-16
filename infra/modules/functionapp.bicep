@description('Azure region for Function App resources.')
param location string

@description('Name of the Function App.')
param functionAppName string

@description('Storage account name used by the Function App.')
param storageAccountName string

@description('TRAPI endpoint URL.')
param trapiEndpoint string

@description('TRAPI deployment name.')
param trapiDeploymentName string = 'gpt-4o'

@description('TRAPI API version.')
param trapiApiVersion string = '2024-02-01'

@description('Application Insights connection string.')
param appInsightsConnectionString string = ''

@description('Key Vault SecretUri used for TRAPI credential reference.')
param trapiCredentialSecretUri string = ''

@description('Tags applied to Function App resources.')
param tags object = {}

var baseAppSettings = [
  {
    name: 'AzureWebJobsStorage__accountName'
    value: storageAccountName
  }
  {
    name: 'FUNCTIONS_WORKER_RUNTIME'
    value: 'python'
  }
  {
    name: 'FUNCTIONS_EXTENSION_VERSION'
    value: '~4'
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
]

var appInsightsSettings = empty(appInsightsConnectionString)
  ? []
  : [
      {
        name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
        value: appInsightsConnectionString
      }
    ]

var keyVaultReferenceSettings = empty(trapiCredentialSecretUri)
  ? []
  : [
      {
        name: 'TRAPI_API_KEY'
        value: '@Microsoft.KeyVault(SecretUri=${trapiCredentialSecretUri})'
      }
    ]

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: '${functionAppName}-plan'
  location: location
  tags: tags
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  kind: 'functionapp'
  properties: {
    reserved: true
  }
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      minTlsVersion: '1.2'
      appSettings: concat(baseAppSettings, appInsightsSettings, keyVaultReferenceSettings)
    }
  }
}

output functionAppName string = functionApp.name
output functionAppPrincipalId string = functionApp.identity.principalId
