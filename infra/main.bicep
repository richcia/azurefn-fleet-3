param location string = resourceGroup().location
param tags object = {}

@minLength(3)
@maxLength(24)
param dataStorageAccountName string = 'y${uniqueString(resourceGroup().id)}data'

@minLength(3)
@maxLength(24)
param hostStorageAccountName string = 'y${uniqueString(resourceGroup().id)}host'

resource hostStorageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: hostStorageAccountName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

module dataStorage './modules/storage.bicep' = {
  name: 'data-storage'
  params: {
    storageAccountName: dataStorageAccountName
    location: location
    tags: tags
  }
}

output dataStorageAccountName string = dataStorage.outputs.storageAccountName
output dataStorageAccountId string = dataStorage.outputs.storageAccountId
output hostStorageAccountName string = hostStorageAccount.name
