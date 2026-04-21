param principalId string
param dataStorageAccountName string
param dataContainerName string
param hostStorageAccountName string

var blobDataContributorRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
var queueDataContributorRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '974c5e8b-45b9-4653-ba55-5f855dd0fb88')

resource dataStorageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: dataStorageAccountName
}

resource dataBlobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' existing = {
  parent: dataStorageAccount
  name: 'default'
}

resource dataContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' existing = {
  parent: dataBlobService
  name: dataContainerName
}

resource hostStorageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: hostStorageAccountName
}

resource dataContainerRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(dataContainer.id, principalId, blobDataContributorRoleDefinitionId)
  scope: dataContainer
  properties: {
    principalId: principalId
    roleDefinitionId: blobDataContributorRoleDefinitionId
    principalType: 'ServicePrincipal'
  }
}

resource hostStorageQueueRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(hostStorageAccount.id, principalId, queueDataContributorRoleDefinitionId)
  scope: hostStorageAccount
  properties: {
    principalId: principalId
    roleDefinitionId: queueDataContributorRoleDefinitionId
    principalType: 'ServicePrincipal'
  }
}

resource hostStorageBlobRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(hostStorageAccount.id, principalId, blobDataContributorRoleDefinitionId)
  scope: hostStorageAccount
  properties: {
    principalId: principalId
    roleDefinitionId: blobDataContributorRoleDefinitionId
    principalType: 'ServicePrincipal'
  }
}

output dataContainerRoleAssignmentId string = dataContainerRoleAssignment.id
output hostStorageQueueRoleAssignmentId string = hostStorageQueueRoleAssignment.id
output hostStorageBlobRoleAssignmentId string = hostStorageBlobRoleAssignment.id
