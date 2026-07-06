param kvtName string
param location string
@secure()
param nerSecret string
@secure()
param nerSecretPassword string
@secure()
param ocrSecret string
@secure()
param ocrSecretPassword string
param org string

resource kv 'Microsoft.KeyVault/vaults@2021-11-01-preview' = {
  name: kvtName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    accessPolicies: [
    ]
    tenantId: '8336fc64-6a89-4d8b-9434-4746d5d32119'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
      ipRules: []
      virtualNetworkRules: []
    }
    vaultUri: 'https://${kvtName}${environment().suffixes.keyvaultDns}'
    provisioningState: 'Succeeded'
    publicNetworkAccess: 'Enabled'
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enableRbacAuthorization: true
    enablePurgeProtection: (org == 'dev') ? null : true
  }
}

resource ner_kv 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  parent: kv
  name: nerSecret 
  properties: {
    contentType: nerSecret
    value: nerSecretPassword
    attributes: {
      enabled: true
    }
  }
}

resource ocr_kv 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  parent: kv
  name: ocrSecret
  properties: {
    contentType: ocrSecret
    value: ocrSecretPassword
    attributes: {
      enabled: true
    }
  }
}
