@description('Function App managed identity principal ID.')
param principalId string

@description('Resource ID of the yankees-roster blob container.')
param blobContainerResourceId string

@description('Resource ID of the Key Vault.')
param keyVaultResourceId string

module rbac './modules/rbac.bicep' = {
  name: 'rbacAssignments'
  params: {
    principalId: principalId
    blobContainerResourceId: blobContainerResourceId
    keyVaultResourceId: keyVaultResourceId
  }
}
