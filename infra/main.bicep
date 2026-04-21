param location string = resourceGroup().location
param tags object = {
  project: '1985-NY-Yankees'
  owner: 'rciapala'
}
param trapiEndpoint string
param trapiDeploymentName string
@secure()
param trapiFallbackCredential string = ''

var nameSuffix = uniqueString(resourceGroup().id)
var functionAppName = 'func-${nameSuffix}'
var dataStorageAccountName = 'st${take(uniqueString(resourceGroup().id, 'data'), 22)}'
var hostStorageAccountName = 'st${take(uniqueString(resourceGroup().id, 'host'), 22)}'
var keyVaultName = 'kv-${nameSuffix}'

module dataStorage './modules/storage.bicep' = {
  name: 'dataStorage'
  params: {
    storageAccountName: dataStorageAccountName
    location: location
    tags: tags
    accessTier: 'Cool'
    blobDeleteRetentionDays: 7
    containerDeleteRetentionDays: 7
    containerName: 'yankees-roster'
    createContainer: true
  }
}

module hostStorage './modules/storage.bicep' = {
  name: 'hostStorage'
  params: {
    storageAccountName: hostStorageAccountName
    location: location
    tags: tags
    accessTier: 'Hot'
    blobDeleteRetentionDays: 7
    containerDeleteRetentionDays: 7
    createContainer: false
  }
}

module functionApp './modules/functionapp.bicep' = {
  name: 'functionApp'
  params: {
    functionAppName: functionAppName
    location: location
    tags: tags
    hostStorageAccountName: hostStorage.outputs.storageAccountName
    trapiEndpointSettingValue: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=TRAPI-ENDPOINT)'
    trapiDeploymentNameSettingValue: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=TRAPI-DEPLOYMENT-NAME)'
    trapiFallbackCredentialSettingValue: empty(trapiFallbackCredential) ? '' : '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=TRAPI-FALLBACK-CREDENTIAL)'
  }
}

module keyVault './modules/keyvault.bicep' = {
  name: 'keyVault'
  params: {
    keyVaultName: keyVaultName
    location: location
    tags: tags
    functionPrincipalId: functionApp.outputs.principalId
    trapiEndpoint: trapiEndpoint
    trapiDeploymentName: trapiDeploymentName
    trapiFallbackCredential: trapiFallbackCredential
  }
}

module rbac './modules/rbac.bicep' = {
  name: 'rbac'
  params: {
    principalId: functionApp.outputs.principalId
    dataStorageAccountName: dataStorage.outputs.storageAccountName
    dataContainerName: dataStorage.outputs.containerName
    hostStorageAccountName: hostStorage.outputs.storageAccountName
  }
}

output functionAppName string = functionApp.outputs.functionAppName
output functionPrincipalId string = functionApp.outputs.principalId
output dataStorageAccountName string = dataStorage.outputs.storageAccountName
output hostStorageAccountName string = hostStorage.outputs.storageAccountName
output dataContainerResourceId string = dataStorage.outputs.containerResourceId
output keyVaultName string = keyVault.outputs.keyVaultName
