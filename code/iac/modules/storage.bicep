param stgName string
param location string
param storageSku string = 'Standard_LRS'
param storageKind string = 'StorageV2'
param properties object = {
  immutableStorageWithVersioning: {
    enabled: false
  }
  defaultEncryptionScope: '$account-encryption-key'
  denyEncryptionScopeOverride: false
  publicAccess: 'None'
}
param blobContainers array
param tableContainers array
param kvtName string

resource storage 'Microsoft.Storage/storageAccounts@2021-09-01' = {
  name: stgName
  location: location
  sku: {
    name: storageSku
  }
  kind: storageKind
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    defaultToOAuthAuthentication: false
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    networkAcls: {
      bypass: 'AzureServices'
      virtualNetworkRules: []
      ipRules: []
      defaultAction: 'Allow'
    }
    supportsHttpsTrafficOnly: true
    encryption: {
      services: {
        file: {
          keyType: 'Account'
          enabled: true
        }
        blob: {
          keyType: 'Account'
          enabled: true
        }
      }
      keySource: 'Microsoft.Storage'
    }
    accessTier: 'Hot'
  }
}

resource containersHosts 'Microsoft.Storage/storageAccounts/blobServices/containers@2021-09-01' = [for (name,i) in blobContainers: {
  name: '${storage.name}${name}'
  properties: properties
}]

resource containersBlobTrigger 'Microsoft.Storage/storageAccounts/queueServices/queues@2021-09-01' = {
  name: '${storage.name}/default/azure-webjobs-blobtrigger-chromadiverseapp'
}

resource tableClients 'Microsoft.Storage/storageAccounts/tableServices/tables@2021-09-01' = [for (name,i) in tableContainers: {
  name: '${storage.name}${name}'
}]

resource storage_connection_string 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  name: '${kvtName}/${storage.name}-ConnectionString'
  properties: {
    contentType: 'Connection String with key1 for storage account'
    value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${listKeys(storage.id, storage.apiVersion).keys[0].value};EndpointSuffix=${environment().suffixes.storage}'
    attributes: {
      enabled: true
    }
  }
}

resource storage_key_string 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  name: '${kvtName}/${storage.name}-key'
  properties: {
    contentType: 'key1 for storage account'
    value: '${listKeys(storage.id, storage.apiVersion).keys[0].value}'
    attributes: {
      enabled: true
    }
  }
}

output stgKeyvaultRef string = storage_connection_string.properties.secretUriWithVersion
output stgKeyvaultKeyRef string = storage_key_string.properties.secretUriWithVersion
