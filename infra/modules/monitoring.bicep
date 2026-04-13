@description('Azure region for monitoring resources.')
param location string

@description('Name of the Log Analytics Workspace.')
param logAnalyticsWorkspaceName string

@description('Name of the Application Insights instance.')
param appInsightsName string

@description('Resource tags applied to all resources in this module.')
param tags object = {}

// ---------------------------------------------------------------------------
// Log Analytics Workspace
// ---------------------------------------------------------------------------

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// ---------------------------------------------------------------------------
// Application Insights (workspace-based)
// ---------------------------------------------------------------------------

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
    RetentionInDays: 30
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------

@description('The resource ID of the Application Insights instance.')
output appInsightsId string = appInsights.id

@description('The Application Insights connection string.')
output appInsightsConnectionString string = appInsights.properties.ConnectionString

@description('The instrumentation key of the Application Insights instance.')
output appInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey

@description('The resource ID of the Log Analytics Workspace.')
output logAnalyticsWorkspaceId string = logAnalyticsWorkspace.id
