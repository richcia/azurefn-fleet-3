param name string
param location string = resourceGroup().location
param tags object = {}
param tenantId string = subscription().tenantId
param softDeleteRetentionInDays int = 90
param enablePurgeProtection bool = true
param trapiCredentialSecretName string = 'trapi-credential'
param createTrapiCredentialSecret bool = false
@secure()
param trapiCredentialSecretValue string = ''

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    enableRbacAuthorization: true
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: false
    enablePurgeProtection: enablePurgeProtection
    softDeleteRetentionInDays: softDeleteRetentionInDays
    tenantId: tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
  }
}

resource trapiCredentialSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (createTrapiCredentialSecret) {
  parent: keyVault
  name: trapiCredentialSecretName
  properties: {
    value: trapiCredentialSecretValue
  }
}

output keyVaultName string = keyVault.name
output keyVaultResourceId string = keyVault.id
output keyVaultUri string = keyVault.properties.vaultUri
output trapiCredentialSecretUri string = createTrapiCredentialSecret
  ? '${keyVault.properties.vaultUri}secrets/${trapiCredentialSecretName}'
  : ''
