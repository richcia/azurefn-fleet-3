param location string
param logAnalyticsWorkspaceName string
param applicationInsightsName string
param tags object = {}

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  properties: {
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
  }
  tags: tags
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: applicationInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
    RetentionInDays: 30
  }
  tags: tags
}

output applicationInsightsConnectionString string = applicationInsights.properties.ConnectionString
output applicationInsightsId string = applicationInsights.id
output logAnalyticsWorkspaceId string = logAnalyticsWorkspace.id
