@description('Principal ID of the Function App system-assigned managed identity')
param functionPrincipalId string

@description('Principal ID of the staging deployment slot system-assigned managed identity')
param stagingSlotPrincipalId string

@description('Name of the dedicated data storage account')
param dataStorageAccountName string

@description('Name of the blob container in the dedicated data storage account')
param dataContainerName string

@description('Name of the host storage account')
param hostStorageAccountName string

@description('Name of the Key Vault')
param keyVaultName string

// ---------------------------------------------------------------------------
// Built-in role definition IDs (Azure built-in roles)
// ---------------------------------------------------------------------------

var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var storageQueueDataContributorRoleId = '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
var storageTableDataContributorRoleId = '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
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

resource dataContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' existing = {
  name: dataContainerName
  parent: dataBlobService
}

// ---------------------------------------------------------------------------
// Storage Blob Data Contributor — scoped to the data container
// ---------------------------------------------------------------------------

resource dataContainerBlobContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(dataContainer.id, functionPrincipalId, storageBlobDataContributorRoleId)
  scope: dataContainer
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
// Storage Table Data Contributor — scoped to the host storage account
// (required by the Functions v4 runtime for distributed lock/lease management)
// ---------------------------------------------------------------------------

resource hostStorageTableContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(hostStorageAccount.id, functionPrincipalId, storageTableDataContributorRoleId)
  scope: hostStorageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageTableDataContributorRoleId)
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

// ---------------------------------------------------------------------------
// Storage Blob Data Contributor — staging slot MI scoped to the data container
// (allows staging slot to perform smoke tests against the yankees-roster container)
// ---------------------------------------------------------------------------

resource stagingSlotDataContainerBlobContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(dataContainer.id, stagingSlotPrincipalId, storageBlobDataContributorRoleId)
  scope: dataContainer
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
    principalId: stagingSlotPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// ---------------------------------------------------------------------------
// Host storage role assignments — staging slot MI
// The Functions v4 runtime (identity-based AzureWebJobsStorage) requires
// Blob, Queue, and Table Data Contributor on the host storage account so the
// slot can acquire leases, manage triggers, and write runtime logs.
// ---------------------------------------------------------------------------

resource stagingSlotHostBlobAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(hostStorageAccount.id, stagingSlotPrincipalId, storageBlobDataContributorRoleId)
  scope: hostStorageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
    principalId: stagingSlotPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource stagingSlotHostQueueAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(hostStorageAccount.id, stagingSlotPrincipalId, storageQueueDataContributorRoleId)
  scope: hostStorageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageQueueDataContributorRoleId)
    principalId: stagingSlotPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource stagingSlotHostTableAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(hostStorageAccount.id, stagingSlotPrincipalId, storageTableDataContributorRoleId)
  scope: hostStorageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageTableDataContributorRoleId)
    principalId: stagingSlotPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// ---------------------------------------------------------------------------
// Key Vault Secrets User — staging slot MI scoped to the Key Vault
// Required so Key Vault references (TRAPI_ENDPOINT, TRAPI_DEPLOYMENT_NAME)
// resolve correctly on the staging slot.
// ---------------------------------------------------------------------------

resource stagingSlotKeyVaultSecretsUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVaultResource.id, stagingSlotPrincipalId, keyVaultSecretsUserRoleId)
  scope: keyVaultResource
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
    principalId: stagingSlotPrincipalId
    principalType: 'ServicePrincipal'
  }
}
