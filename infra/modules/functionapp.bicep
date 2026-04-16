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

@description('Optional Key Vault URI used to build TRAPI setting references')
param keyVaultUri string = ''

@description('TRAPI endpoint value when not using Key Vault references')
param trapiEndpoint string = ''

@description('TRAPI auth scope value when not using Key Vault references')
param trapiAuthScope string = ''

@description('Key Vault secret name for TRAPI endpoint')
param trapiEndpointSecretName string = 'trapi-endpoint'

@description('Key Vault secret name for TRAPI auth scope')
param trapiAuthScopeSecretName string = 'trapi-auth-scope'

@description('Optional staging slot override for TRAPI endpoint')
param stagingTrapiEndpoint string = ''

@description('Optional staging slot override for TRAPI auth scope')
param stagingTrapiAuthScope string = ''

var productionTrapiEndpoint = empty(keyVaultUri)
  ? trapiEndpoint
  : '@Microsoft.KeyVault(SecretUri=${keyVaultUri}secrets/${trapiEndpointSecretName}/)'

var productionTrapiAuthScope = empty(keyVaultUri)
  ? trapiAuthScope
  : '@Microsoft.KeyVault(SecretUri=${keyVaultUri}secrets/${trapiAuthScopeSecretName}/)'

var stagingTrapiEndpointValue = empty(stagingTrapiEndpoint) ? productionTrapiEndpoint : stagingTrapiEndpoint
var stagingTrapiAuthScopeValue = empty(stagingTrapiAuthScope) ? productionTrapiAuthScope : stagingTrapiAuthScope

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
          value: productionTrapiEndpoint
        }
        {
          name: 'TRAPI_AUTH_SCOPE'
          value: productionTrapiAuthScope
        }
      ]
    }
  }
}

resource functionAppStagingSlot 'Microsoft.Web/sites/slots@2022-09-01' = {
  name: '${functionApp.name}/staging'
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
  name: '${functionApp.name}/slotConfigNames'
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
