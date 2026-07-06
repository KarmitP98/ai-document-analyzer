param acrName string
param location string
param acrSku string = 'Standard'
param quarantinePolicyStatus string = 'disabled'
param trustPolicyType string = 'Notary'
param trustPolicyStatus string = 'disabled'
param retentionPolicyDays int = 7
param retentionPolicyStatus string = 'disabled'
param exportPolicyStatus string = 'enabled'
param fxnMIobjectId string


var roleIdMapping = {
  AcrDelete: 'c2f4ef07-c644-48eb-af81-4b1b4947fb11'
  AcrImageSigner: '6cef56e8-d556-48e5-a04f-b8e64114680f'
  AcrPull: '7f951dda-4ed3-4680-a7ca-43fe172d538d'
  AcrPush: '8311e382-0749-4cb8-b61a-304f252e45ec'
  AcrQuarantineReader: 'cdda3590-29a3-44f6-95f2-9f980659eb04'
  AcrQuarantineWriter: 'c8d4ff99-41c3-41a8-9f60-21dfdad59608'
}
@description('Specifies the role the user will get with the secret in the vault. Valid values are: AcrDelete, AcrImageSigner, AcrPull, AcrPush, AcrQuarantineReader, AcrQuarantineWriter.')
@allowed([
  'AcrDelete'
  'AcrImageSigner'
  'AcrPull'
  'AcrPush'
  'AcrQuarantineReader'
  'AcrQuarantineWriter'
])
param roleName string = 'AcrPull'

resource acr 'Microsoft.ContainerRegistry/registries@2021-12-01-preview' = {
  name: acrName
  location: location
   sku: {
    name: acrSku
  }
  identity: {
    type:'SystemAssigned'
  }
  properties: {
    adminUserEnabled: true
    policies: {
      quarantinePolicy: {
        status: quarantinePolicyStatus
      }
      trustPolicy: {
        type: trustPolicyType
        status: trustPolicyStatus
      }
      retentionPolicy: {
        days: retentionPolicyDays
        status: retentionPolicyStatus
      }
      exportPolicy: {
        status: exportPolicyStatus
      }
    }
    encryption: {
      status: 'disabled'
    }
    dataEndpointEnabled: false
    publicNetworkAccess: 'Enabled'
    networkRuleBypassOptions: 'AzureServices'
    zoneRedundancy: 'Disabled'
    anonymousPullEnabled: false
  }
}

resource acr_authz 'Microsoft.Authorization/roleAssignments@2020-10-01-preview' = {
  name: guid(roleIdMapping[roleName], fxnMIobjectId, acr.id)
  scope:acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleIdMapping[roleName])
    principalId: fxnMIobjectId
    principalType: 'ServicePrincipal'
  }
}


output acrMIobjectID string = acr.identity.principalId
