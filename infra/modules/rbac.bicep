@description('Principal ID of the Function App system-assigned managed identity')
param functionPrincipalId string

@description('Name of the dedicated data storage account')
param dataStorageAccountName string

@description('Name of the host storage account')
param hostStorageAccountName string

@description('Name of the Key Vault')
param keyVaultName string

// ---------------------------------------------------------------------------
// Built-in role definition IDs (Azure built-in roles)
// ---------------------------------------------------------------------------

var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var storageQueueDataContributorRoleId = '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e0'

// ---------------------------------------------------------------------------
// Existing resource references (data storage)
// ---------------------------------------------------------------------------

resource dataStorageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' existing = {
  name: dataStorageAccountName
}

resource dataBlobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' existing = {
  name: 'default'
  parent: dataStorageAccount
}

resource yankeesRosterContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' existing = {
  name: 'yankees-roster'
  parent: dataBlobService
}

// ---------------------------------------------------------------------------
// Storage Blob Data Contributor — scoped to the yankees-roster container
// ---------------------------------------------------------------------------

resource dataContainerBlobContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(yankeesRosterContainer.id, functionPrincipalId, storageBlobDataContributorRoleId)
  scope: yankeesRosterContainer
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
    principalId: functionPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// ---------------------------------------------------------------------------
// Existing resource references (host storage)
// ---------------------------------------------------------------------------

resource hostStorageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' existing = {
  name: hostStorageAccountName
}

// ---------------------------------------------------------------------------
// Storage Blob Data Contributor — scoped to the host storage account
// ---------------------------------------------------------------------------

resource hostStorageBlobContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(hostStorageAccount.id, functionPrincipalId, storageBlobDataContributorRoleId)
  scope: hostStorageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
    principalId: functionPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// ---------------------------------------------------------------------------
// Storage Queue Data Contributor — scoped to the host storage account
// ---------------------------------------------------------------------------

resource hostStorageQueueContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(hostStorageAccount.id, functionPrincipalId, storageQueueDataContributorRoleId)
  scope: hostStorageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageQueueDataContributorRoleId)
    principalId: functionPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// ---------------------------------------------------------------------------
// Key Vault Secrets User — scoped to the Key Vault
// ---------------------------------------------------------------------------

resource keyVaultResource 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource keyVaultSecretsUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVaultResource.id, functionPrincipalId, keyVaultSecretsUserRoleId)
  scope: keyVaultResource
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
    principalId: functionPrincipalId
    principalType: 'ServicePrincipal'
  }
}
