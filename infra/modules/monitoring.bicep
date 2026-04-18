@description('Azure region for monitoring resources.')
param location string = resourceGroup().location

@description('Resource name prefix used for monitoring resources.')
param namePrefix string = 'yankees'

var resourceSuffix = uniqueString(resourceGroup().id)
var samplingSettings = {
  isEnabled: true
  excludedTypes: 'Request;Exception'
}

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: toLower('${namePrefix}-law-${resourceSuffix}')
  location: location
  properties: {
    retentionInDays: 30
  }
  sku: {
    name: 'PerGB2018'
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: toLower('${namePrefix}-appi-${resourceSuffix}')
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
    RetentionInDays: 30
    IngestionMode: 'LogAnalytics'
  }
}

output logAnalyticsWorkspaceId string = logAnalyticsWorkspace.id
output applicationInsightsId string = appInsights.id
output applicationInsightsConnectionString string = appInsights.properties.ConnectionString
output samplingSettings object = samplingSettings
