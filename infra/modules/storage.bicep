@description('Azure region for all resources')
param location string

@description('Resource tags')
param tags object

@description('Name of the dedicated data storage account')
param dataStorageAccountName string

@description('Name of the host/runtime storage account used by the Function App')
param hostStorageAccountName string

@description('Name of the blob container in the dedicated data storage account')
param dataContainerName string

// ---------------------------------------------------------------------------
// Dedicated data storage account (Standard_LRS, Cool, no shared-key access)
// ---------------------------------------------------------------------------

resource dataStorageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: dataStorageAccountName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Cool'
    allowSharedKeyAccess: false
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource dataBlobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  name: 'default'
  parent: dataStorageAccount
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

resource yankeesRosterContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: dataContainerName
  parent: dataBlobService
  properties: {
    publicAccess: 'None'
  }
}

// ---------------------------------------------------------------------------
// Host storage account (used by the Functions runtime)
// ---------------------------------------------------------------------------

resource hostStorageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: hostStorageAccountName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    allowSharedKeyAccess: false
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource hostBlobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  name: 'default'
  parent: hostStorageAccount
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------

output dataStorageAccountName string = dataStorageAccount.name
output dataStorageAccountId string = dataStorageAccount.id
output dataContainerResourceId string = yankeesRosterContainer.id

output hostStorageAccountName string = hostStorageAccount.name
output hostStorageAccountId string = hostStorageAccount.id
