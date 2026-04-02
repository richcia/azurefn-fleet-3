@description('Name of the Storage Account to scope the role assignment to.')
param storageAccountName string

@description('Principal ID of the Function App Managed Identity.')
param principalId string

// Storage Blob Data Owner — required for the Azure Functions runtime to manage
// host blob leases when using managed-identity-based AzureWebJobsStorage.
var storageBlobDataOwnerRoleId = 'b7e6dc9b-827d-4af3-a56f-e6d3a4e7765d'

// Storage Queue Data Contributor — required for the Functions runtime to enqueue
// and dequeue messages on the host storage queues.
var storageQueueDataContributorRoleId = '974c5e8b-45b9-4653-ba55-5f855dd0fb88'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' existing = {
  name: storageAccountName
}

resource blobOwnerAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, principalId, storageBlobDataOwnerRoleId)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataOwnerRoleId)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}

resource queueContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, principalId, storageQueueDataContributorRoleId)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageQueueDataContributorRoleId)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
