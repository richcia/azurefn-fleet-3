targetScope = 'resourceGroup'

param location string = resourceGroup().location
param tags object = {
  project: '1985-NY-Yankees'
  owner: 'rciapala'
}

@description('Function App system-assigned managed identity principal ID.')
param functionAppPrincipalId string

@description('Globally unique Key Vault name (3-24 chars, alphanumeric and hyphen).')
param keyVaultName string = 'kv-${uniqueString(resourceGroup().id)}'

param trapiCredentialSecretName string = 'trapi-credential'
param createTrapiCredentialSecret bool = false

@secure()
@description('Optional TRAPI credential value. Leave empty when TRAPI uses managed identity auth.')
param trapiCredentialSecretValue string = ''

module keyVault './modules/keyvault.bicep' = {
  name: 'keyVault'
  params: {
    name: keyVaultName
    location: location
    tags: tags
    trapiCredentialSecretName: trapiCredentialSecretName
    createTrapiCredentialSecret: createTrapiCredentialSecret
    trapiCredentialSecretValue: trapiCredentialSecretValue
  }
}

module keyVaultRbac './modules/rbac.bicep' = {
  name: 'keyVaultRbac'
  params: {
    principalId: functionAppPrincipalId
    keyVaultResourceId: keyVault.outputs.keyVaultResourceId
  }
}

output keyVaultName string = keyVault.outputs.keyVaultName
output keyVaultResourceId string = keyVault.outputs.keyVaultResourceId
output keyVaultUri string = keyVault.outputs.keyVaultUri
output keyVaultSecretsUserAssignmentId string = keyVaultRbac.outputs.keyVaultSecretsUserAssignmentId
output trapiCredentialSecretUri string = keyVault.outputs.trapiCredentialSecretUri
output trapiCredentialSecretReference string = !empty(keyVault.outputs.trapiCredentialSecretUri)
  ? '@Microsoft.KeyVault(SecretUri=${keyVault.outputs.trapiCredentialSecretUri})'
  : ''
