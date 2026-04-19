@description('Deployment location.')
param location string = resourceGroup().location

@description('Existing Function App name to configure with Key Vault references.')
param functionAppName string

@description('Principal ID of the Function App system-assigned managed identity (validated deployment input).')
param functionAppPrincipalId string

@description('Name of the Key Vault to create.')
param keyVaultName string = 'kv${uniqueString(resourceGroup().id)}'

@description('Secret name used for fallback TRAPI credentials in Key Vault references.')
param trapiFallbackSecretName string = 'trapi-fallback-credential'

@allowed([
  true
])
@description('Set to true after confirming the selected region supports zone-redundant Key Vault.')
param zoneRedundancyRegionConfirmed bool = true

@description('Resource tags.')
param tags object = {
  project: '1985-NY-Yankees'
  owner: 'rciapala'
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' existing = {
  name: functionAppName
}

var existingAppSettings = list('${functionApp.id}/config/appsettings', '2023-12-01').properties

module keyVault 'modules/keyvault.bicep' = {
  name: 'keyVaultModule'
  params: {
    keyVaultName: keyVaultName
    location: location
    functionAppPrincipalId: functionAppPrincipalId
    zoneRedundancyRegionConfirmed: zoneRedundancyRegionConfirmed
    tags: tags
  }
}

resource functionAppAppSettings 'Microsoft.Web/sites/config@2023-12-01' = {
  name: 'appsettings'
  parent: functionApp
  properties: union(existingAppSettings, {
    KEY_VAULT_URI: keyVault.outputs.keyVaultUri
    TRAPI_FALLBACK_CREDENTIAL: '@Microsoft.KeyVault(SecretUri=${keyVault.outputs.keyVaultUri}secrets/${trapiFallbackSecretName}/)'
  })
}

output keyVaultId string = keyVault.outputs.keyVaultId
output keyVaultName string = keyVault.outputs.keyVaultName
output keyVaultUri string = keyVault.outputs.keyVaultUri
