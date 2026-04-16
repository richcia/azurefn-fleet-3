@description('Azure region for the Key Vault resource.')
param location string

@description('Name of the Key Vault to create.')
param keyVaultName string

@description('Tags applied to the Key Vault resource.')
param tags object = {}

@description('Secret name used by the Function App for TRAPI credentials.')
param trapiSecretName string = 'trapi-api-key'

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    tenantId: tenant().tenantId
    enableRbacAuthorization: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    sku: {
      family: 'A'
      name: 'standard'
    }
  }
}

output keyVaultUri string = keyVault.properties.vaultUri
output keyVaultId string = keyVault.id
output trapiSecretUri string = '${keyVault.properties.vaultUri}secrets/${trapiSecretName}'
