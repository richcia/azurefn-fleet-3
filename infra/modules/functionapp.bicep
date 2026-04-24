@description('Azure region for all resources')
param location string

@description('Resource tags')
param tags object

@description('Base name used to derive resource names')
param baseName string

// ---------------------------------------------------------------------------
// Consumption App Service Plan (Linux)
// ---------------------------------------------------------------------------

resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: 'asp-${baseName}'
  location: location
  tags: tags
  kind: 'functionapp'
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true
  }
}

// ---------------------------------------------------------------------------
// Function App (Python 3.11, system-assigned MI, identity-based storage)
// App settings are applied via a separate Microsoft.Web/sites/config resource
// in main.bicep *after* the Key Vault Secrets User RBAC assignment completes,
// to avoid 403 errors when the runtime resolves Key Vault references.
// ---------------------------------------------------------------------------

resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: 'fn-${baseName}'
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    reserved: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
    }
    httpsOnly: true
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------

output functionAppName string = functionApp.name
output functionPrincipalId string = functionApp.identity.principalId
