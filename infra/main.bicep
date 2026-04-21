param location string = resourceGroup().location
param tags object = {
  project: '1985-NY-Yankees'
  owner: 'rciapala'
}
param alertEmailAddress string

var nameSuffix = uniqueString(resourceGroup().id)
var functionAppName = 'func-${nameSuffix}'
var dataStorageAccountName = 'st${take(uniqueString(resourceGroup().id, 'data'), 22)}'
var hostStorageAccountName = 'st${take(uniqueString(resourceGroup().id, 'host'), 22)}'
var logAnalyticsWorkspaceName = 'law-${nameSuffix}'
var appInsightsName = 'appi-${nameSuffix}'

module dataStorage './modules/storage.bicep' = {
  name: 'dataStorage'
  params: {
    storageAccountName: dataStorageAccountName
    location: location
    tags: tags
    accessTier: 'Cool'
    blobDeleteRetentionDays: 7
    containerDeleteRetentionDays: 7
    containerName: 'yankees-roster'
    createContainer: true
  }
}

module hostStorage './modules/storage.bicep' = {
  name: 'hostStorage'
  params: {
    storageAccountName: hostStorageAccountName
    location: location
    tags: tags
    accessTier: 'Hot'
    blobDeleteRetentionDays: 7
    containerDeleteRetentionDays: 7
    createContainer: false
  }
}

module monitoring './modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    tags: tags
    workspaceName: logAnalyticsWorkspaceName
    applicationInsightsName: appInsightsName
  }
}

module functionApp './modules/functionapp.bicep' = {
  name: 'functionApp'
  params: {
    functionAppName: functionAppName
    location: location
    tags: tags
    hostStorageAccountName: hostStorage.outputs.storageAccountName
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
  }
}

module rbac './modules/rbac.bicep' = {
  name: 'rbac'
  params: {
    principalId: functionApp.outputs.principalId
    dataStorageAccountName: dataStorage.outputs.storageAccountName
    dataContainerName: dataStorage.outputs.containerName
    hostStorageAccountName: hostStorage.outputs.storageAccountName
  }
}

module alerts './modules/alerts.bicep' = {
  name: 'alerts'
  params: {
    location: location
    tags: tags
    functionAppName: functionApp.outputs.functionAppName
    logAnalyticsWorkspaceId: monitoring.outputs.workspaceId
    alertEmailAddress: alertEmailAddress
  }
}

output functionAppName string = functionApp.outputs.functionAppName
output functionPrincipalId string = functionApp.outputs.principalId
output dataStorageAccountName string = dataStorage.outputs.storageAccountName
output hostStorageAccountName string = hostStorage.outputs.storageAccountName
output dataContainerResourceId string = dataStorage.outputs.containerResourceId
output appInsightsId string = monitoring.outputs.appInsightsId
output logAnalyticsWorkspaceId string = monitoring.outputs.workspaceId
