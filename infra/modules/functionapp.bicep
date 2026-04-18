param location string
param functionAppName string
param servicePlanName string
param storageAccountName string
param applicationInsightsConnectionString string
param trapiEndpoint string = ''
param trapiDeploymentName string = 'gpt-4o'
param trapiApiVersion string = '2024-02-01'
param tags object = {}

resource servicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: servicePlanName
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
  properties: {
    serverFarmId: servicePlan.id
    reserved: true
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      appSettings: [
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: applicationInsightsConnectionString
        }
        {
          name: 'AzureWebJobsStorage__accountName'
          value: storageAccountName
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'STORAGE_ACCOUNT_NAME'
          value: storageAccountName
        }
        {
          name: 'TRAPI_API_VERSION'
          value: trapiApiVersion
        }
        {
          name: 'TRAPI_DEPLOYMENT_NAME'
          value: trapiDeploymentName
        }
        {
          name: 'TRAPI_ENDPOINT'
          value: trapiEndpoint
        }
        {
          name: 'WEBSITE_RUN_FROM_PACKAGE'
          value: '1'
        }
      ]
    }
  }
  tags: tags
}

output functionAppId string = functionApp.id
output functionAppName string = functionApp.name
output functionAppPrincipalId string = functionApp.identity.principalId!
