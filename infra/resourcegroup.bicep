targetScope = 'subscription'

@description('Name of the resource group to create')
param resourceGroupName string = 'rg-1985-ny-yankees'

@description('Azure region for the resource group')
param location string = 'eastus'

@description('Project name tag value')
param projectName string = '1985-NY-Yankees'

@description('Owner tag value')
param ownerName string = 'rciapala'

var tags = {
  project: projectName
  owner: ownerName
}

resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

output resourceGroupName string = rg.name
output resourceGroupId string = rg.id
