@description('Azure region for resources')
param location string = resourceGroup().location

@description('Function App name')
param functionAppName string

@description('App Service plan resource ID')
param servicePlanId string

@description('Host storage account name used by Azure Functions runtime')
param hostStorageAccountName string

@description('Dedicated application data storage account name for production slot')
param dataStorageAccountName string

@description('Dedicated application data storage account name for staging slot')
param stagingDataStorageAccountName string

@description('TRAPI endpoint used by production slot')
param trapiEndpoint string

@description('TRAPI endpoint used by staging slot')
param stagingTrapiEndpoint string

@description('Additional app settings shared by production and staging slots')
param sharedAppSettings array = []

@description('Resource tags')
param tags object = {}

var storageBlobDataContributorRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')

resource stagingDataStorageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' existing = {
  name: stagingDataStorageAccountName
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  tags: tags
  properties: {
    serverFarmId: servicePlanId
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      minTlsVersion: '1.2'
      appSettings: concat([
        {
          name: 'AzureWebJobsStorage__accountName'
          value: hostStorageAccountName
        }
        {
          name: 'DATA_STORAGE_ACCOUNT_NAME'
          value: dataStorageAccountName
        }
        {
          name: 'TRAPI_ENDPOINT'
          value: trapiEndpoint
        }
      ], sharedAppSettings)
    }
  }
}

resource slotStickySettings 'Microsoft.Web/sites/config@2023-12-01' = {
  name: 'slotConfigNames'
  parent: functionApp
  properties: {
    appSettingNames: [
      'DATA_STORAGE_ACCOUNT_NAME'
      'TRAPI_ENDPOINT'
    ]
  }
}

resource stagingSlot 'Microsoft.Web/sites/slots@2023-12-01' = {
  name: 'staging'
  parent: functionApp
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: servicePlanId
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      minTlsVersion: '1.2'
      appSettings: concat([
        {
          name: 'AzureWebJobsStorage__accountName'
          value: hostStorageAccountName
        }
        {
          name: 'DATA_STORAGE_ACCOUNT_NAME'
          value: stagingDataStorageAccountName
        }
        {
          name: 'TRAPI_ENDPOINT'
          value: stagingTrapiEndpoint
        }
      ], sharedAppSettings)
    }
  }
}

resource stagingSlotStorageBlobDataContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(stagingDataStorageAccount.id, stagingSlot.id, storageBlobDataContributorRoleId)
  scope: stagingDataStorageAccount
  properties: {
    principalId: stagingSlot.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: storageBlobDataContributorRoleId
  }
}

output functionAppId string = functionApp.id
output functionAppPrincipalId string = functionApp.identity.principalId
output stagingSlotPrincipalId string = stagingSlot.identity.principalId
output stagingSlotHostname string = stagingSlot.properties.defaultHostName
