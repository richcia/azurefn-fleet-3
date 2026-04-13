@description('Azure region for the Storage Account.')
param location string = resourceGroup().location

@description('Name of the Storage Account (must be globally unique, 3-24 lowercase alphanumeric chars).')
param storageAccountName string

@description('Resource tags applied to all resources in this module.')
param tags object = {}

// ---------------------------------------------------------------------------
// Storage Account
// ---------------------------------------------------------------------------

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    accessTier: 'Hot'
    // Disable shared-key access so only identity-based auth (AzureWebJobsStorage__accountName) is used
    allowSharedKeyAccess: false
  }
}

// ---------------------------------------------------------------------------
// Blob Service
// ---------------------------------------------------------------------------

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

// ---------------------------------------------------------------------------
// Blob Container: yankees-roster
// ---------------------------------------------------------------------------

resource yankeesRosterContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'yankees-roster'
  properties: {
    publicAccess: 'None'
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------

@description('The name of the provisioned Storage Account.')
output storageAccountName string = storageAccount.name

@description('The resource ID of the provisioned Storage Account.')
output storageAccountId string = storageAccount.id
