@description('Azure region for all resources.')
param location string

@description('Short prefix used to name resources.')
param prefix string

@description('Resource tags applied to all resources.')
param tags object

// Strip hyphens, underscores, dots, and spaces so the name is lowercase alphanumeric only.
var normalizedPrefix = toLower(replace(replace(replace(replace(prefix, '-', ''), '_', ''), '.', ''), ' ', ''))
var storageAccountName = take('st${normalizedPrefix}${uniqueString(resourceGroup().id)}', 24)
var blobContainerName = 'yankees-roster'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    accessTier: 'Hot'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: blobContainerName
  properties: {
    publicAccess: 'None'
  }
}

output storageAccountName string = storageAccount.name
output storageAccountId string = storageAccount.id
output blobContainerName string = blobContainer.name
