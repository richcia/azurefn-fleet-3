@description('Azure region for all resources. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('Project name used for tagging')
param projectName string = '1985-NY-Yankees'

@description('Owner name used for tagging')
param ownerName string = 'rciapala'

@description('Storage account name (lowercase, 3-24 alphanumeric characters, globally unique)')
param storageAccountName string = 'st1985nyyankees'

@description('Function App name (must be globally unique)')
param functionAppName string = 'func-1985-ny-yankees'

@description('App Service Plan name')
param appServicePlanName string = 'asp-1985-ny-yankees'

@description('Application Insights instance name')
param appInsightsName string = 'appi-1985-ny-yankees'

@description('Log Analytics Workspace name')
param logAnalyticsWorkspaceName string = 'law-1985-ny-yankees'

var tags = {
  project: projectName
  owner: ownerName
}

module storage './modules/storage.bicep' = {
  name: 'storage'
  params: {
    location: location
    storageAccountName: storageAccountName
    tags: tags
  }
}

module monitoring './modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
    appInsightsName: appInsightsName
    tags: tags
  }
}

module functionApp './modules/functionapp.bicep' = {
  name: 'functionapp'
  params: {
    location: location
    appServicePlanName: appServicePlanName
    functionAppName: functionAppName
    storageAccountName: storage.outputs.storageAccountName
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    tags: tags
  }
}

output storageAccountName string = storage.outputs.storageAccountName
output storageAccountId string = storage.outputs.storageAccountId
output appInsightsId string = monitoring.outputs.appInsightsId
output logAnalyticsWorkspaceId string = monitoring.outputs.logAnalyticsWorkspaceId
output functionAppId string = functionApp.outputs.functionAppId
output functionAppName string = functionApp.outputs.functionAppName
output functionAppPrincipalId string = functionApp.outputs.functionAppPrincipalId
output functionAppHostname string = functionApp.outputs.functionAppHostname
