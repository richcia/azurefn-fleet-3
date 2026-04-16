@description('Location for Function App resources')
param location string

@description('Tags applied to all resources')
param tags object = {}

@description('Name of the Function App')
param functionAppName string

@description('Name of the backing storage account for AzureWebJobsStorage identity-based connection')
param storageAccountName string

@description('Connection string from the monitoring module output')
param applicationInsightsConnectionString string

@description('TRAPI endpoint setting value. Pass plain endpoint text or a Key Vault reference string.')
@minLength(1)
param trapiEndpointSetting string

@description('TRAPI auth scope setting value. Pass plain scope text or a Key Vault reference string.')
@minLength(1)
param trapiAuthScopeSetting string

@description('Optional staging slot override for TRAPI endpoint')
param stagingTrapiEndpointSetting string = ''

@description('Optional staging slot override for TRAPI auth scope')
param stagingTrapiAuthScopeSetting string = ''

var stagingTrapiEndpointValue = empty(stagingTrapiEndpointSetting) ? trapiEndpointSetting : stagingTrapiEndpointSetting
var stagingTrapiAuthScopeValue = empty(stagingTrapiAuthScopeSetting) ? trapiAuthScopeSetting : stagingTrapiAuthScopeSetting

resource functionPlan 'Microsoft.Web/serverfarms@2022-09-01' = {
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

resource functionApp 'Microsoft.Web/sites@2022-09-01' = {
  name: functionAppName
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: functionPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
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
          name: 'WEBSITE_RUN_FROM_PACKAGE'
          value: '1'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: applicationInsightsConnectionString
        }
        {
          name: 'AzureWebJobsStorage__accountName'
          value: storageAccountName
        }
        {
          name: 'TRAPI_ENDPOINT'
          value: trapiEndpointSetting
        }
        {
          name: 'TRAPI_AUTH_SCOPE'
          value: trapiAuthScopeSetting
        }
      ]
    }
  }
}

resource functionAppStagingSlot 'Microsoft.Web/sites/slots@2022-09-01' = {
  name: 'staging'
  parent: functionApp
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: functionPlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
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
          name: 'WEBSITE_RUN_FROM_PACKAGE'
          value: '1'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: applicationInsightsConnectionString
        }
        {
          name: 'AzureWebJobsStorage__accountName'
          value: storageAccountName
        }
        {
          name: 'TRAPI_ENDPOINT'
          value: stagingTrapiEndpointValue
        }
        {
          name: 'TRAPI_AUTH_SCOPE'
          value: stagingTrapiAuthScopeValue
        }
      ]
    }
  }
}

resource slotConfigNames 'Microsoft.Web/sites/config@2022-09-01' = {
  name: 'slotConfigNames'
  parent: functionApp
  properties: {
    appSettingNames: [
      'TRAPI_ENDPOINT'
      'TRAPI_AUTH_SCOPE'
    ]
  }
}

output functionAppId string = functionApp.id
output functionAppPrincipalId string = functionApp.identity.principalId
output functionAppNameOut string = functionApp.name
