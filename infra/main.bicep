@description('Azure region for deployed resources.')
param location string = resourceGroup().location

@description('Globally unique storage account name for dedicated roster data storage.')
@minLength(3)
@maxLength(24)
param storageAccountName string = 'yr${uniqueString(resourceGroup().id)}'

@description('Function App host storage account name used for AzureWebJobsStorage, to verify separation from dedicated roster storage.')
param functionHostStorageAccountName string = ''

@description('Tags to apply to provisioned resources.')
param tags object = {
  project: '1985-NY-Yankees'
  owner: 'rciapala'
}

module storage './modules/storage.bicep' = {
  name: 'storageDeployment'
  params: {
    storageAccountName: storageAccountName
    location: location
    tags: tags
  }
}

var storageDistinctFromHost = empty(functionHostStorageAccountName) || toLower(storage.outputs.storageAccountName) != toLower(functionHostStorageAccountName)

output storageAccountName string = storage.outputs.storageAccountName
output storageAccountResourceId string = storage.outputs.storageAccountId
output yankeesRosterContainerName string = storage.outputs.yankeesRosterContainerName
output storageDistinctFromHost bool = storageDistinctFromHost
