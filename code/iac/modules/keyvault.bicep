param kvtName string
param location string
param kvKeys array

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
    tenantId: 'cb3b0d1e-24fb-4847-ba48-2f5e7c2b9b23'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'allow'
      virtualNetworkRules: []
    }
    vaultUri: 'https://${kvtName}${environment().suffixes.keyvaultDns}'
    provisioningState: 'Succeeded'
    publicNetworkAccess: 'Enabled'
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: false
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enableRbacAuthorization: true
    enablePurgeProtection: true
  }
}

resource resource_kv 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = [for (name, i) in kvKeys: {
  parent: kv
  name: '${name}'
  properties: {
    contentType: '${name}'
    attributes: {
      enabled: true
    }
  }
}]

