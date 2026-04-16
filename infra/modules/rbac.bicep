@description('Function App managed identity principal ID.')
param functionPrincipalId string

@description('Storage account name.')
param storageAccountName string

@description('Key Vault name.')
param keyVaultName string

var storageBlobDataContributorRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
)

var keyVaultSecretsUserRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '4633458b-17de-408a-b874-0445c86b69e6'
)

var storageQueueDataContributorRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
)

var storageTableDataContributorRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
)

resource storageBlobDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, functionPrincipalId, storageBlobDataContributorRoleDefinitionId)
  scope: storageAccount
  properties: {
    principalId: functionPrincipalId
    roleDefinitionId: storageBlobDataContributorRoleDefinitionId
    principalType: 'ServicePrincipal'
  }
}

resource storageQueueDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, functionPrincipalId, storageQueueDataContributorRoleDefinitionId)
  scope: storageAccount
  properties: {
    principalId: functionPrincipalId
    roleDefinitionId: storageQueueDataContributorRoleDefinitionId
    principalType: 'ServicePrincipal'
  }
}

resource storageTableDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, functionPrincipalId, storageTableDataContributorRoleDefinitionId)
  scope: storageAccount
  properties: {
    principalId: functionPrincipalId
    roleDefinitionId: storageTableDataContributorRoleDefinitionId
    principalType: 'ServicePrincipal'
  }
}

resource keyVaultSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, functionPrincipalId, keyVaultSecretsUserRoleDefinitionId)
  scope: keyVault
  properties: {
    principalId: functionPrincipalId
    roleDefinitionId: keyVaultSecretsUserRoleDefinitionId
    principalType: 'ServicePrincipal'
  }
}

output storageBlobDataContributorAssignmentId string = storageBlobDataContributor.id
output storageQueueDataContributorAssignmentId string = storageQueueDataContributor.id
output storageTableDataContributorAssignmentId string = storageTableDataContributor.id
output keyVaultSecretsUserAssignmentId string = keyVaultSecretsUser.id

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}
