param keyVaultName string
param location string
param tags object = {}
param functionPrincipalId string
param trapiEndpoint string
param trapiDeploymentName string
@secure()
param trapiFallbackCredential string = ''

var keyVaultSecretsUserRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')

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
    enabledForTemplateDeployment: true
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

resource functionAppSecretsUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, functionPrincipalId, keyVaultSecretsUserRoleDefinitionId)
  scope: keyVault
  properties: {
    principalId: functionPrincipalId
    roleDefinitionId: keyVaultSecretsUserRoleDefinitionId
    principalType: 'ServicePrincipal'
  }
}

output keyVaultName string = keyVault.name
output keyVaultId string = keyVault.id
output trapiEndpointSecretName string = trapiEndpointSecret.name
output trapiDeploymentNameSecretName string = trapiDeploymentNameSecret.name
