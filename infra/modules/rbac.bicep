@description('Function App managed identity principal ID.')
param principalId string

@description('Resource ID of the yankees-roster blob container.')
param blobContainerResourceId string

@description('Resource ID of the Key Vault.')
param keyVaultResourceId string

var storageBlobDataContributorRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
var keyVaultSecretsUserRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')

var blobContainerResourceIdSegments = split(blobContainerResourceId, '/')
var storageAccountName = blobContainerResourceIdSegments[8]
var blobContainerName = blobContainerResourceIdSegments[12]

var keyVaultResourceIdSegments = split(keyVaultResourceId, '/')
var keyVaultName = keyVaultResourceIdSegments[8]

resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' existing = {
  name: '${storageAccountName}/default/${blobContainerName}'
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource blobContainerStorageBlobDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(blobContainer.id, principalId, storageBlobDataContributorRoleDefinitionId)
  scope: blobContainer
  properties: {
    roleDefinitionId: storageBlobDataContributorRoleDefinitionId
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}

resource keyVaultSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, principalId, keyVaultSecretsUserRoleDefinitionId)
  scope: keyVault
  properties: {
    roleDefinitionId: keyVaultSecretsUserRoleDefinitionId
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
