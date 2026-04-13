@description('Azure region for all resources. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('Project identifier used for tagging.')
param project string = '1985-NY-Yankees'

@description('Owner identifier used for tagging.')
param owner string = 'rciapala'

@description('TRAPI (Azure OpenAI) endpoint URL.')
param trapiEndpoint string

@description('TRAPI deployment name (model alias).')
param trapiDeploymentName string = 'gpt-4o'

@description('TRAPI API version.')
param trapiApiVersion string = '2024-02-01'

@description('Email address to receive function-exception alert notifications.')
param alertEmailAddress string = 'ops-alerts@example.com'

// ---------------------------------------------------------------------------
// Variables
// ---------------------------------------------------------------------------

var tags = {
  project: project
  owner: owner
}

// Storage Account names must be 3-24 lowercase alphanumeric characters and globally unique.
// uniqueString produces a deterministic 13-char hash from the resource group ID.
// 'st' (2) + uniqueString (13) = 15 chars — within the 3-24 char limit.
var storageAccountName = 'st${uniqueString(resourceGroup().id)}'

// Function App names must be globally unique.
// 'fn' (2) + uniqueString (13) = 15 chars — within limits.
var functionAppName = 'fn${uniqueString(resourceGroup().id)}'

// Monitoring resource names derived from resource group ID for uniqueness.
var logAnalyticsWorkspaceName = 'law${uniqueString(resourceGroup().id)}'
var appInsightsName = 'appi${uniqueString(resourceGroup().id)}'
var actionGroupName = '${functionAppName}-ag'
var exceptionAlertRuleName = '${functionAppName}-exceptions-alert'

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

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoringDeployment'
  params: {
    location: location
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
    appInsightsName: appInsightsName
    tags: tags
  }
}

module functionapp 'modules/functionapp.bicep' = {
  name: 'functionappDeployment'
  params: {
    location: location
    functionAppName: functionAppName
    storageAccountName: storageAccountName
    trapiEndpoint: trapiEndpoint
    trapiDeploymentName: trapiDeploymentName
    trapiApiVersion: trapiApiVersion
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    tags: tags
  }
}

module alerts 'modules/alerts.bicep' = {
  name: 'alertsDeployment'
  params: {
    location: location
    actionGroupName: actionGroupName
    alertEmailAddress: alertEmailAddress
    alertRuleName: exceptionAlertRuleName
    appInsightsId: monitoring.outputs.appInsightsId
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

@description('Name of the provisioned Function App.')
output functionAppName string = functionapp.outputs.functionAppName

@description('Resource ID of the provisioned Function App.')
output functionAppId string = functionapp.outputs.functionAppId

@description('Principal ID of the Function App system-assigned managed identity. Use for RBAC assignments.')
output functionAppPrincipalId string = functionapp.outputs.principalId

@description('Default hostname of the Function App.')
output functionAppDefaultHostname string = functionapp.outputs.defaultHostname

@description('Resource ID of the Application Insights instance.')
output appInsightsId string = monitoring.outputs.appInsightsId

@description('Application Insights connection string. Set as APPLICATIONINSIGHTS_CONNECTION_STRING in the Function App.')
output appInsightsConnectionString string = monitoring.outputs.appInsightsConnectionString

@description('Resource ID of the Log Analytics Workspace backing Application Insights.')
output logAnalyticsWorkspaceId string = monitoring.outputs.logAnalyticsWorkspaceId

@description('Resource ID of the exception alert rule.')
output exceptionAlertRuleId string = alerts.outputs.exceptionAlertRuleId
