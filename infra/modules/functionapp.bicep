@description('Azure region for the Function App.')
param location string

@description('Function App name.')
param functionAppName string

@description('App Service plan name for Linux Consumption hosting.')
param appServicePlanName string

@description('Host storage account name for identity-based AzureWebJobsStorage configuration.')
param hostStorageAccountName string

@description('Application Insights connection string.')
@secure()
param applicationInsightsConnectionString string

@description('Key Vault name used for app-setting references.')
param keyVaultName string

@description('Key Vault secret name for TRAPI endpoint.')
param trapiEndpointSecretName string = 'TRAPI-ENDPOINT'

@description('TRAPI auth scope used by DefaultAzureCredential for bearer tokens.')
@allowed([
  'https://cognitiveservices.azure.com/.default'
])
param trapiAuthScope string = 'https://cognitiveservices.azure.com/.default'

@description('Key Vault secret name for data storage account name.')
param dataStorageAccountNameSecretName string = 'DATA-STORAGE-ACCOUNT-NAME'

@description('Optional resource tags.')
param tags object = {}

resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: appServicePlanName
  location: location
  kind: 'functionapp,linux'
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true
  }
  tags: tags
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  tags: tags
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      appSettings: [
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'AzureWebJobsStorage__accountName'
          value: hostStorageAccountName
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: applicationInsightsConnectionString
        }
        {
          name: 'TRAPI_ENDPOINT'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=${trapiEndpointSecretName})'
        }
        {
          name: 'TRAPI_AUTH_SCOPE'
          value: trapiAuthScope
        }
        {
          name: 'DATA_STORAGE_ACCOUNT_NAME'
          value: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=${dataStorageAccountNameSecretName})'
        }
      ]
    }
  }
}

output functionAppId string = functionApp.id
output functionAppName string = functionApp.name
output principalId string = functionApp.identity.principalId
