@description('Azure region for all resources. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('Short prefix used to name resources (3–11 alphanumeric characters).')
@minLength(3)
@maxLength(11)
param prefix string = 'yankees85'

@description('Application Insights connection string for Function App observability. Leave empty to omit.')
@secure()
param appInsightsConnectionString string = ''

var tags = {
  project: '1985-NY-Yankees'
  owner: 'rciapala'
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    location: location
    prefix: prefix
    tags: tags
  }
}

module functionApp 'modules/functionapp.bicep' = {
  name: 'functionApp'
  params: {
    location: location
    prefix: prefix
    tags: tags
    storageAccountName: storage.outputs.storageAccountName
    appInsightsConnectionString: appInsightsConnectionString
  }
}

// Grant the Function App's Managed Identity the roles needed for identity-based
// AzureWebJobsStorage: Storage Blob Data Owner (runtime host blobs) and
// Storage Queue Data Contributor (runtime host queues).
module rbac 'modules/rbac.bicep' = {
  name: 'rbac'
  params: {
    storageAccountName: storage.outputs.storageAccountName
    principalId: functionApp.outputs.principalId
  }
}

output storageAccountName string = storage.outputs.storageAccountName
output blobContainerName string = storage.outputs.blobContainerName
output functionAppName string = functionApp.outputs.functionAppName
output functionAppPrincipalId string = functionApp.outputs.principalId
