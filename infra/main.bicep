param location string = resourceGroup().location
param storageAccountName string
param functionAppName string = 'func-${uniqueString(resourceGroup().id)}'
param servicePlanName string = 'plan-${uniqueString(resourceGroup().id)}'
param logAnalyticsWorkspaceName string = 'log-${uniqueString(resourceGroup().id)}'
param applicationInsightsName string = 'appi-${uniqueString(resourceGroup().id)}'
param trapiEndpoint string = ''
param trapiDeploymentName string = 'gpt-4o'
param trapiApiVersion string = '2024-02-01'
param tags object = {
  project: '1985-NY-Yankees'
  owner: 'rciapala'
}

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
    applicationInsightsName: applicationInsightsName
    tags: tags
  }
}

module functionApp 'modules/functionapp.bicep' = {
  name: 'functionapp'
  params: {
    location: location
    functionAppName: functionAppName
    servicePlanName: servicePlanName
    storageAccountName: storageAccountName
    applicationInsightsConnectionString: monitoring.outputs.applicationInsightsConnectionString
    trapiEndpoint: trapiEndpoint
    trapiDeploymentName: trapiDeploymentName
    trapiApiVersion: trapiApiVersion
    tags: tags
  }
}

output functionAppId string = functionApp.outputs.functionAppId
output functionAppName string = functionApp.outputs.functionAppName
output functionAppPrincipalId string = functionApp.outputs.functionAppPrincipalId
