targetScope = 'subscription'

param org string
param app string
param env string
param location string = deployment().location
param blobContainers array
param tableContainers array
@secure()
param nerSecret string
@secure()
param nerSecretPassword string
@secure()
param ocrSecret string
@secure()
param ocrSecretPassword string

param autoscale object

@maxLength(2)
param loc string
param tags object
param rgIndex string

param subDomain string
param dnsZone string
param agwFirewallMode string

@secure()
param listenerCert string

param platformRGName string = toUpper('MNPD-CC-${env}-INFRA-RG-01')
param vnetName string = toUpper('MNPD-CC-${env}-INFRA-VNET-01')


@description('Role to be assigned to Function App MID, defaulting to "storage blob data owner"')
var fxc2stgBlobRole = 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'

@description('Role to be assigned to Function App MID, defaulting to "storage table data contributor"')
var fxc2stgTableRole = '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'

@description('Role to be assigned to Function App MID, defaulting to "key vault secrets user"')
var fxc2kvtRole = '4633458b-17de-408a-b874-0445c86b69e6'


var rgName = toUpper('MNPD-${loc}-${app}-${org}-RG-${rgIndex}')
var aspName = toLower('${app}${org}asp01')
var stgName = toLower('${app}${org}stg01')
var acrName = toLower('${app}${org}acr01')
var kvtName = toLower('${app}${org}kvt01')
var ocrName = toLower('${app}${org}ocr01')
var nerName = toLower('${app}${org}ner01')
var fxcName = toLower('${app}${org}fxc01')
var webName = toLower('${app}${org}web01')
var agwName = toLower('${app}${org}agw01')
var UAMIDName = toLower('${app}${org}agwmid01')

var agwSubnetID = '${platformvnet.id}/subnets/MNPD-CC-${env}-AGW-SUB-01'

resource rg 'Microsoft.Resources/resourceGroups@2020-10-01' = {
  name: rgName
  location: location
  tags: tags
}

resource platformRG 'Microsoft.Resources/resourceGroups@2020-10-01' existing = {
  name: platformRGName
}

resource platformvnet 'Microsoft.Network/virtualNetworks@2022-01-01' existing = {
  name: vnetName
  scope: platformRG
}

module appGateway 'modules/appGateway.bicep' = {
  scope: platformRG
  name: 'appGateway_Deployment'
  params: {
    location: location
    name: agwName
    subnetId: agwSubnetID
    firewallMode: agwFirewallMode
    userAssignedID: userAssignedManagedID.outputs.identityId
    appFQDN: webApp.outputs.appFQDN
    appServiceName: webName
    listenerCert: listenerCert
    subDomain: subDomain
    dnsZone: dnsZone
  }
}

module userAssignedManagedID 'modules/user-assigned-identity.bicep' = {
  scope: platformRG
  name: 'UserAssignedMID_Deployment'
  params: {
    location: location
    name: UAMIDName
  }
}

module appService 'modules/appService.bicep' = {
  scope: rg
  name: 'appService_Deployment'
  params: {
    aspName: aspName
    location: location
    autoscale: autoscale
  }
}

module containerRegistry 'modules/acr.bicep' = {
  scope: rg
  name: 'containerRegistry_Deployment'
  params: {
    acrName: acrName
    location: location
    fxnMIobjectId: functionApp.outputs.fxnMIobjectID
    
  }
}

module cognitiveServices 'modules/cognitiveServices.bicep' = {
  scope: rg
  name: 'cognitiveServices_Deployment'
  dependsOn: [
    workloadKeyvault
  ]
  params: {
    ocrName: ocrName
    nerName: nerName
    location: location
    kvtName: kvtName
  }
}

module workloadKeyvault 'modules/workloadkeyvault.bicep' = {
  scope: rg
  name: 'keyvault_Deployment'
  params: {
    kvtName: kvtName
    location: location
    nerSecret: nerSecret
    nerSecretPassword: nerSecretPassword
    ocrSecret: ocrSecret
    ocrSecretPassword: ocrSecretPassword
    org: org
  }
}

module storage 'modules/storage.bicep' = {
  scope: rg
  name: 'storage_Deployment'
  dependsOn: [
    workloadKeyvault
  ]
  params: {
    stgName: stgName
    location: location
    blobContainers: blobContainers
    tableContainers: tableContainers
    kvtName: kvtName
  }
}

module appInsights 'modules/appInsights.bicep' = {
  scope: rg
  name: 'appInsight_Deployment'
  params: {
    appInsName: fxcName
    location: location
  }
}

module functionApp 'modules/functionApp.bicep' = {
  scope: rg
  name: 'functionApp_Deployment'
  dependsOn: [
    workloadKeyvault
  ]
  params: {
    functionAppName: fxcName
    location: location
    serverfarmID: appService.outputs.planId
    acrName: acrName
  }
}


module fxc2stgBlobRoleAssignement 'modules/storage-role-assignment-to-sp.bicep' = {
  scope: rg
  name: 'roleAssignment_fxc2stgBlob'
  params: {
    roleDefinitionId: fxc2stgBlobRole
    storageAccountName: stgName
    resourceSPObjectIds: array(functionApp.outputs.fxnMIobjectID)
  }
}

module fxc2stgTableRoleAssignement 'modules/storage-role-assignment-to-sp.bicep' = {
  scope: rg
  name: 'roleAssignment_fxc2stgTable'
  params: {
    roleDefinitionId: fxc2stgTableRole
    storageAccountName: stgName
    resourceSPObjectIds: array(functionApp.outputs.fxnMIobjectID)
  }
}

module fxc2kvtRoleAssignement 'modules/key-vault-role-assignment-to-sp.bicep' = {
  scope: rg
  name: 'roleAssignment_fxc2kvt'
  params: {
    keyVaultName: kvtName
    roleDefinitionId: fxc2kvtRole
    resourceSPObjectIds: array(functionApp.outputs.fxnMIobjectID)
  }
}

module webApp 'modules/webApp.bicep' = {
  scope: rg
  name: 'webApp_Deployment'
  params: {
    webAppName: webName
    location: location
    serverfarmID: appService.outputs.planId
    platformRGName: platformRGName
    dnsZone: dnsZone
    subDomain: subDomain
  }
}

module siteConfig_FunctionApp 'modules/siteConfig_functionapp.bicep' = {
  scope: rg
  name: 'functionApp_SettingConfig'
  params: {
    functionAppName: fxcName
    storagename: stgName
    acrName: acrName
    ocrname: ocrName
    taname: nerName
    appInsightsKey: appInsights.outputs.appInsightsKey
    nerKeyvaultRef: cognitiveServices.outputs.nerKeyvaultRef
    ocrKeyvaultRef: cognitiveServices.outputs.ocrKeyvaultRef
    stgKeyvaultRef: storage.outputs.stgKeyvaultRef
    stgKeyvaultKeyRef: storage.outputs.stgKeyvaultKeyRef
  }
  dependsOn: [
    functionApp
    containerRegistry
    cognitiveServices
    storage
  ]
}

module siteConfig_WebApp 'modules/siteConfig_webapp.bicep' = {
  scope: rg
  name: 'webApp_SettingConfig'
  params: {
    agwPublicIp: appGateway.outputs.agwPublicIp
    webAppName: webName
    storageName: stgName
    functionName: fxcName
  }
}
