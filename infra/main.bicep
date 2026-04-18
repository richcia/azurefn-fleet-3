@description('Azure region for deployed resources.')
param location string = resourceGroup().location

@description('Globally unique storage account name for dedicated roster data storage.')
@minLength(3)
@maxLength(24)
param storageAccountName string = 'yr${uniqueString(resourceGroup().id)}'

@description('Function App host storage account name used for AzureWebJobsStorage, to verify separation from dedicated roster storage.')
@minLength(3)
@maxLength(24)
param functionHostStorageAccountName string

@description('Tags to apply to provisioned resources.')
param tags object = {
  project: '1985-NY-Yankees'
  owner: 'rciapala'
}

var storageDistinctFromHost = toLower(storageAccountName) != toLower(functionHostStorageAccountName)

module storage './modules/storage.bicep' = if (storageDistinctFromHost) {
  name: 'storageDeployment'
  params: {
    storageAccountName: storageAccountName
    location: location
    tags: tags
  }
}

resource storageNameValidationGuard 'Microsoft.Storage/storageAccounts@2023-05-01' = if (!storageDistinctFromHost) {
  name: '${take(storageAccountName, 23)}-'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
}

output storageAccountName string = storageDistinctFromHost ? storage!.outputs.storageAccountName : ''
output storageAccountResourceId string = storageDistinctFromHost ? storage!.outputs.storageAccountId : ''
output yankeesRosterContainerName string = storageDistinctFromHost ? storage!.outputs.yankeesRosterContainerName : ''
output storageDistinctFromHost bool = storageDistinctFromHost
