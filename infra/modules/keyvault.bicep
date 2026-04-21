param keyVaultName string
param location string
param tags object = {}
param trapiEndpoint string
param trapiDeploymentName string
@secure()
param trapiFallbackCredential string = ''

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    tenantId: tenant().tenantId
    sku: {
      family: 'A'
      name: 'premium'
    }
    enableRbacAuthorization: true
    enabledForTemplateDeployment: false
    softDeleteRetentionInDays: 90
    publicNetworkAccess: 'Enabled'
  }
}

resource trapiEndpointSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'TRAPI-ENDPOINT'
  properties: {
    value: trapiEndpoint
  }
}

resource trapiDeploymentNameSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'TRAPI-DEPLOYMENT-NAME'
  properties: {
    value: trapiDeploymentName
  }
}

resource trapiFallbackCredentialSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(trapiFallbackCredential)) {
  parent: keyVault
  name: 'TRAPI-FALLBACK-CREDENTIAL'
  properties: {
    value: trapiFallbackCredential
  }
}

output keyVaultName string = keyVault.name
output keyVaultId string = keyVault.id
output trapiEndpointSecretName string = trapiEndpointSecret.name
output trapiDeploymentNameSecretName string = trapiDeploymentNameSecret.name
