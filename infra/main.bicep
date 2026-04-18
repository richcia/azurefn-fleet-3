@description('Function App managed identity principal ID.')
param principalId string

@description('Resource ID of the yankees-roster blob container.')
param blobContainerResourceId string

@description('Resource ID of the Key Vault.')
param keyVaultResourceId string

@description('Azure region for alert resources.')
param location string = resourceGroup().location

@description('Resource ID of the Application Insights instance.')
param applicationInsightsResourceId string

@description('Email address for rciapala alert notifications.')
param rciapalaEmailAddress string

@description('Optional resource tags.')
param tags object = {}

module rbac './modules/rbac.bicep' = {
  name: 'rbacAssignments'
  params: {
    principalId: principalId
    blobContainerResourceId: blobContainerResourceId
    keyVaultResourceId: keyVaultResourceId
  }
}

module alerts './modules/alerts.bicep' = {
  name: 'alerts'
  params: {
    location: location
    applicationInsightsResourceId: applicationInsightsResourceId
    rciapalaEmailAddress: rciapalaEmailAddress
    tags: tags
  }
}
