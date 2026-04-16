param location string = resourceGroup().location
@description('Function App host storage account name (AzureWebJobsStorage).')
param hostStorageAccountName string
@description('Dedicated storage account name for application roster data.')
param rosterStorageAccountName string = 'roster${uniqueString(resourceGroup().id)}'
param tags object = {
  project: '1985-NY-Yankees'
  owner: 'rciapala'
}

var normalizedHostStorageName = toLower(hostStorageAccountName)
var normalizedRosterStorageName = toLower(rosterStorageAccountName)
var effectiveRosterStorageAccountName = normalizedRosterStorageName == normalizedHostStorageName
  ? take('${normalizedRosterStorageName}data', 24)
  : normalizedRosterStorageName

module rosterStorage './modules/storage.bicep' = {
  name: 'rosterStorage'
  params: {
    storageAccountName: effectiveRosterStorageAccountName
    location: location
    tags: tags
  }
}

output dedicatedStorageAccountName string = rosterStorage.outputs.storageAccountResourceName
output rosterContainerName string = rosterStorage.outputs.rosterContainerName
