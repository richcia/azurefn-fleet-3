@description('Globally unique name for the dedicated application storage account.')
param storageAccountName string

@description('Azure region for the storage account.')
param location string = resourceGroup().location

@description('Tags to apply to the storage account.')
param tags object = {}

resource dedicatedStorageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  tags: tags
  properties: {
    accessTier: 'Cool'
    allowSharedKeyAccess: false
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  name: 'default'
  parent: dedicatedStorageAccount
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

resource yankeesRosterContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  name: 'yankees-roster'
  parent: blobService
  properties: {
    publicAccess: 'None'
  }
}

output storageAccountName string = dedicatedStorageAccount.name
output storageAccountId string = dedicatedStorageAccount.id
output yankeesRosterContainerName string = yankeesRosterContainer.name
