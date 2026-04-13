@description('Azure region for all resources. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('Project identifier used for tagging.')
param project string = '1985-NY-Yankees'

@description('Owner identifier used for tagging.')
param owner string = 'rciapala'

// ---------------------------------------------------------------------------
// Variables
// ---------------------------------------------------------------------------

var tags = {
  project: project
  owner: owner
}

// Storage Account names must be 3-24 lowercase alphanumeric characters and globally unique.
// uniqueString produces a deterministic 13-char hash from the resource group ID.
var storageAccountName = 'st${uniqueString(resourceGroup().id)}'

// ---------------------------------------------------------------------------
// Modules
// ---------------------------------------------------------------------------

module storage 'modules/storage.bicep' = {
  name: 'storageDeployment'
  params: {
    location: location
    storageAccountName: storageAccountName
    tags: tags
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------

@description('Name of the provisioned Storage Account. Use this as AzureWebJobsStorage__accountName.')
output storageAccountName string = storage.outputs.storageAccountName

@description('Resource ID of the provisioned Storage Account.')
output storageAccountId string = storage.outputs.storageAccountId
