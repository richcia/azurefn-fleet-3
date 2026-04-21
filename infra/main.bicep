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
  }
}

module keyVault './modules/keyvault.bicep' = {
  name: 'keyVault'
  params: {
    keyVaultName: keyVaultName
    location: location
    tags: tags
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
    keyVaultName: keyVault.outputs.keyVaultName
  }
}

resource deployedFunctionApp 'Microsoft.Web/sites@2023-12-01' existing = {
  name: functionAppName
}

resource functionAppKeyVaultAppSettings 'Microsoft.Web/sites/config@2023-12-01' = {
  parent: deployedFunctionApp
  name: 'appsettings'
  properties: union({
    FUNCTIONS_EXTENSION_VERSION: '~4'
    FUNCTIONS_WORKER_RUNTIME: 'python'
    AzureWebJobsStorage__accountName: hostStorage.outputs.storageAccountName
    AzureWebJobsStorage__credential: 'managedidentity'
    TRAPI_ENDPOINT: '@Microsoft.KeyVault(VaultName=${keyVault.outputs.keyVaultName};SecretName=TRAPI-ENDPOINT)'
    TRAPI_DEPLOYMENT_NAME: '@Microsoft.KeyVault(VaultName=${keyVault.outputs.keyVaultName};SecretName=TRAPI-DEPLOYMENT-NAME)'
  }, empty(trapiFallbackCredential) ? {} : {
    TRAPI_FALLBACK_CREDENTIAL: '@Microsoft.KeyVault(VaultName=${keyVault.outputs.keyVaultName};SecretName=TRAPI-FALLBACK-CREDENTIAL)'
  })
  dependsOn: [
    rbac
  ]
}

output functionAppName string = functionApp.outputs.functionAppName
output functionPrincipalId string = functionApp.outputs.principalId
output dataStorageAccountName string = dataStorage.outputs.storageAccountName
output hostStorageAccountName string = hostStorage.outputs.storageAccountName
output dataContainerResourceId string = dataStorage.outputs.containerResourceId
output keyVaultName string = keyVault.outputs.keyVaultName
