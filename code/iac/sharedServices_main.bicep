targetScope = 'subscription'

param org string
param app string
param env string
param envCode string
param location string = deployment().location
param kvKeys array

@maxLength(2)
param loc string
param tags object
param rgIndex string

param dnsZone string = 'mnp-ai.ca'

param subnets array
param vnetAddressPrefix string

param deploymentSP array = []
param deploymentSpKvtRole string = '00482a5a-887f-4fb3-b363-3b7fe8e74483'

param deployDnsZone bool

var rgName = toUpper('${org}-${loc}-${env}-${app}-RG-${rgIndex}')
var vnetName = toUpper('${org}-${loc}-${env}-${app}-VNET-${rgIndex}')
var kvtName = toLower('${org}${app}kvt01${envCode}')

resource rg 'Microsoft.Resources/resourceGroups@2020-10-01' = {
  name: rgName
  location: location
  tags: tags
}

module keyvault 'modules/keyvault.bicep' = {
  scope: rg
  name: 'keyvault_Deployment'
  params: {
    kvtName: kvtName
    location: location
    kvKeys: kvKeys
  }
}

module grantSPOPermissionsToKVT 'modules/key-vault-role-assignment-to-sp.bicep' = {
  scope: rg
  name: 'grant_SPOPermissionsToKVT' 
  params: {
    keyVaultName: keyvault.name
    roleDefinitionId: deploymentSpKvtRole
    resourceSPObjectIds: deploymentSP
  }
}

module vnet 'modules/vnet.bicep' = {
  scope: rg
  name: 'vnet_deployment'
  params: {
    subnets: subnets
    vnetAddressPrefix: vnetAddressPrefix
    vnetName: vnetName
    location: location
  }
}

module publicDnsZone 'modules/publicDNSZone.bicep' = if (deployDnsZone) {
  scope: rg
  name: 'dnsZone_deployment'
  params: {
    dnsZone: dnsZone
    location: 'global'
  }
}
