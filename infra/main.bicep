@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Environment label used to make resource names unique.')
param environmentName string = 'staging'

@description('Storage account name used by the Function App for host and application storage.')
param storageAccountName string

@description('TRAPI endpoint URL.')
param trapiEndpoint string

@description('TRAPI deployment name.')
param trapiDeploymentName string = 'gpt-4o'

@description('TRAPI API version.')
param trapiApiVersion string = '2024-02-01'

@description('Application Insights connection string for Function App telemetry.')
param appInsightsConnectionString string = ''

@description('Set to true when TRAPI credentials must come from Key Vault because managed identity auth is not supported.')
param provisionTrapiCredentialKeyVault bool = true

@description('Name of the TRAPI credential secret in Key Vault.')
param trapiSecretName string = 'trapi-api-key'

var tags = {
  project: '1985-NY-Yankees'
  owner: 'rciapala'
}

var keyVaultName = toLower('kv-${environmentName}-${uniqueString(resourceGroup().id)}')
var functionAppName = toLower('func-${environmentName}-${uniqueString(resourceGroup().id)}')

module keyVault './modules/keyvault.bicep' = if (provisionTrapiCredentialKeyVault) {
  name: 'keyVault'
  params: {
    location: location
    keyVaultName: keyVaultName
    tags: tags
    trapiSecretName: trapiSecretName
  }
}

module functionApp './modules/functionapp.bicep' = {
  name: 'functionApp'
  params: {
    location: location
    functionAppName: functionAppName
    storageAccountName: storageAccountName
    trapiEndpoint: trapiEndpoint
    trapiDeploymentName: trapiDeploymentName
    trapiApiVersion: trapiApiVersion
    appInsightsConnectionString: appInsightsConnectionString
    trapiCredentialSecretUri: provisionTrapiCredentialKeyVault ? keyVault!.outputs.trapiSecretUri : ''
    tags: tags
  }
}

output functionAppName string = functionApp.outputs.functionAppName
output keyVaultUri string = provisionTrapiCredentialKeyVault ? keyVault!.outputs.keyVaultUri : ''
