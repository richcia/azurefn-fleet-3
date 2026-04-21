param storageAccountName string
param location string
param tags object = {}
@allowed([
  'Hot'
  'Cool'
])
param accessTier string = 'Hot'
@minValue(1)
@maxValue(365)
param blobDeleteRetentionDays int = 7
@minValue(1)
@maxValue(365)
param containerDeleteRetentionDays int = 7
param containerName string = 'yankees-roster'
param createContainer bool = true

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: accessTier
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  name: 'default'
  parent: storageAccount
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: blobDeleteRetentionDays
    }
    containerDeleteRetentionPolicy: {
      enabled: true
      days: containerDeleteRetentionDays
    }
  }
}

resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = if (createContainer) {
  name: containerName
  parent: blobService
  properties: {
    publicAccess: 'None'
  }
}

output storageAccountName string = storageAccount.name
output storageAccountId string = storageAccount.id
output containerName string = createContainer ? blobContainer.name : ''
output containerResourceId string = createContainer ? blobContainer.id : ''
