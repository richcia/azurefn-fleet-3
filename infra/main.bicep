@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Resource name prefix for generated resources.')
param namePrefix string = 'yankees'

module monitoring './modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    namePrefix: namePrefix
  }
}

module functionapp './modules/functionapp.bicep' = {
  name: 'functionappSettings'
  params: {
    applicationInsightsConnectionString: monitoring.outputs.applicationInsightsConnectionString
    samplingSettings: monitoring.outputs.samplingSettings
  }
}

output applicationInsightsConnectionString string = monitoring.outputs.applicationInsightsConnectionString
output functionAppAppSettings object = functionapp.outputs.appSettings
