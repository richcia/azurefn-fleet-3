param functionAppName string
param location string
param tags object = {}
param hostStorageAccountName string
param trapiEndpointSettingValue string
param trapiDeploymentNameSettingValue string
param trapiFallbackCredentialSettingValue string = ''

var baseAppSettings = [
  {
    name: 'FUNCTIONS_EXTENSION_VERSION'
    value: '~4'
  }
  {
    name: 'FUNCTIONS_WORKER_RUNTIME'
    value: 'python'
  }
  {
    name: 'AzureWebJobsStorage__accountName'
    value: hostStorageAccountName
  }
  {
    name: 'AzureWebJobsStorage__credential'
    value: 'managedidentity'
  }
  {
    name: 'TRAPI_ENDPOINT'
    value: trapiEndpointSettingValue
  }
  {
    name: 'TRAPI_DEPLOYMENT_NAME'
    value: trapiDeploymentNameSettingValue
  }
]

var fallbackCredentialAppSetting = empty(trapiFallbackCredentialSettingValue) ? [] : [
  {
    name: 'TRAPI_FALLBACK_CREDENTIAL'
    value: trapiFallbackCredentialSettingValue
  }
]

resource hostingPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: '${functionAppName}-plan'
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

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: functionAppName
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: hostingPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      minTlsVersion: '1.2'
      appSettings: concat(baseAppSettings, fallbackCredentialAppSetting)
    }
  }
}

output functionAppName string = functionApp.name
output principalId string = functionApp.identity.principalId
output functionAppId string = functionApp.id
