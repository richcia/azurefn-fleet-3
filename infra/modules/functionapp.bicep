@description('Application Insights connection string to set on the Function App.')
param applicationInsightsConnectionString string

@description('Additional app settings to merge with required monitoring settings.')
param additionalAppSettings object = {}

@description('Sampling settings aligned with host.json logging.applicationInsights.samplingSettings.')
param samplingSettings object = {
  isEnabled: true
  excludedTypes: 'Request;Exception'
}

var monitoringAppSettings = {
  APPLICATIONINSIGHTS_CONNECTION_STRING: applicationInsightsConnectionString
  AzureFunctionsJobHost__logging__applicationInsights__samplingSettings__isEnabled: string(samplingSettings.isEnabled)
  AzureFunctionsJobHost__logging__applicationInsights__samplingSettings__excludedTypes: string(samplingSettings.excludedTypes)
}

output appSettings object = union(additionalAppSettings, monitoringAppSettings)
