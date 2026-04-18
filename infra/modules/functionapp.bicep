@description('Function App name.')
param functionAppName string

@description('Consumption hosting plan name.')
param hostingPlanName string

@description('Azure region for Function resources.')
param location string

@description('Dedicated storage account name for identity-based AzureWebJobsStorage.')
param storageAccountName string

@description('Application Insights connection string.')
param appInsightsConnectionString string

@description('TRAPI endpoint URL.')
param trapiEndpoint string

@description('TRAPI deployment name.')
param trapiDeploymentName string

@description('TRAPI API version.')
param trapiApiVersion string

@description('Tags applied to resources.')
param tags object = {}

resource hostingPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: hostingPlanName
  location: location
  kind: 'linux'
  tags: tags
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
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
    serverFarmId: hostingPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      ftpsState: 'Disabled'
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
          value: storageAccountName
        }
        {
          name: 'STORAGE_ACCOUNT_NAME'
          value: storageAccountName
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsightsConnectionString
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
    }
  }
}

output functionAppName string = functionApp.name
output functionAppId string = functionApp.id
output functionAppPrincipalId string = functionApp.identity.principalId
