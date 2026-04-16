targetScope = 'resourceGroup'

@description('Deployment environment name.')
@allowed([
  'staging'
  'prod'
])
param environmentName string

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Prefix used to generate resource names.')
param namePrefix string = 'yankees'

@description('Alert email receiver.')
param alertEmailAddress string

var tags = {
  project: '1985-NY-Yankees'
  owner: 'rciapala'
  environment: environmentName
}

var normalizedPrefix = toLower(replace(namePrefix, '-', ''))
var uniqueness = uniqueString(resourceGroup().id, environmentName)

var storageAccountName = take('${normalizedPrefix}${environmentName}${uniqueness}', 24)
var functionAppName = take('${normalizedPrefix}-${environmentName}-func-${uniqueness}', 60)
var keyVaultName = take('${normalizedPrefix}-${environmentName}-kv-${substring(uniqueness, 0, 4)}', 24)
var workspaceName = take('${normalizedPrefix}-${environmentName}-law-${substring(uniqueness, 0, 6)}', 63)
var appInsightsName = take('${normalizedPrefix}-${environmentName}-appi-${substring(uniqueness, 0, 6)}', 260)
var actionGroupName = take('${normalizedPrefix}-${environmentName}-ag', 64)
var alertRuleName = take('${normalizedPrefix}-${environmentName}-exceptions', 128)

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    storageAccountName: storageAccountName
    location: location
    tags: tags
  }
}

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    workspaceName: workspaceName
    appInsightsName: appInsightsName
    tags: tags
  }
}

module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  params: {
    keyVaultName: keyVaultName
    location: location
    tags: tags
  }
}

module functionapp 'modules/functionapp.bicep' = {
  name: 'functionapp'
  params: {
    functionAppName: functionAppName
    location: location
    storageAccountName: storage.outputs.storageAccountName
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    keyVaultUri: keyvault.outputs.keyVaultUri
    tags: tags
  }
}

module rbac 'modules/rbac.bicep' = {
  name: 'rbac'
  params: {
    functionPrincipalId: functionapp.outputs.functionPrincipalId
    storageAccountName: storage.outputs.storageAccountName
    keyVaultName: keyvault.outputs.keyVaultName
  }
}

module alerts 'modules/alerts.bicep' = {
  name: 'alerts'
  params: {
    location: location
    actionGroupName: actionGroupName
    alertRuleName: alertRuleName
    workspaceResourceId: monitoring.outputs.workspaceId
    alertEmailAddress: alertEmailAddress
    tags: tags
  }
}

output storageAccountName string = storage.outputs.storageAccountName
output storageAccountId string = storage.outputs.storageAccountId
output blobContainerName string = storage.outputs.blobContainerName

output functionAppName string = functionapp.outputs.functionAppName
output functionAppId string = functionapp.outputs.functionAppId
output functionPrincipalId string = functionapp.outputs.functionPrincipalId

output keyVaultName string = keyvault.outputs.keyVaultName
output keyVaultId string = keyvault.outputs.keyVaultId
output keyVaultUri string = keyvault.outputs.keyVaultUri

output logAnalyticsWorkspaceName string = monitoring.outputs.workspaceName
output logAnalyticsWorkspaceId string = monitoring.outputs.workspaceId
output appInsightsName string = monitoring.outputs.appInsightsName
output appInsightsId string = monitoring.outputs.appInsightsId
output appInsightsConnectionString string = monitoring.outputs.appInsightsConnectionString

output actionGroupName string = alerts.outputs.actionGroupName
output actionGroupId string = alerts.outputs.actionGroupId
output exceptionAlertRuleName string = alerts.outputs.alertRuleName
output exceptionAlertRuleId string = alerts.outputs.alertRuleId

output storageBlobDataContributorAssignmentId string = rbac.outputs.storageBlobDataContributorAssignmentId
output storageQueueDataContributorAssignmentId string = rbac.outputs.storageQueueDataContributorAssignmentId
output storageTableDataContributorAssignmentId string = rbac.outputs.storageTableDataContributorAssignmentId
output keyVaultSecretsUserAssignmentId string = rbac.outputs.keyVaultSecretsUserAssignmentId
