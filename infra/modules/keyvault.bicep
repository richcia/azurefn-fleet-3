@description('Azure region for all resources')
param location string

@description('Resource tags')
param tags object

@description('Base name used to derive resource names')
param baseName string

@description('TRAPI endpoint URL to store as a Key Vault secret')
@secure()
param trapiEndpoint string

@description('TRAPI deployment name to store as a Key Vault secret')
@secure()
param trapiDeploymentName string

// ---------------------------------------------------------------------------
// Key Vault (Standard SKU, RBAC authorization model)
// ---------------------------------------------------------------------------

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-${baseName}'
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: tenant().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    enabledForDeployment: false
    enabledForTemplateDeployment: false
    enabledForDiskEncryption: false
    publicNetworkAccess: 'Enabled'
  }
}

// ---------------------------------------------------------------------------
// TRAPI secrets
// ---------------------------------------------------------------------------

resource trapiEndpointSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'trapiEndpoint'
  parent: keyVault
  properties: {
    value: trapiEndpoint
  }
}

resource trapiDeploymentNameSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'trapiDeploymentName'
  parent: keyVault
  properties: {
    value: trapiDeploymentName
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------

output keyVaultName string = keyVault.name
output keyVaultId string = keyVault.id
output keyVaultUri string = keyVault.properties.vaultUri
