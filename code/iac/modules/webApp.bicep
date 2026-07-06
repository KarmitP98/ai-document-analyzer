param webAppName string
param location string
param serverfarmID string
param dnsZone string
param linuxFxVersion string = 'node|16-lts'
param platformRGName string
param subDomain string


resource appservice 'Microsoft.Web/sites@2021-03-01' = {
  name: webAppName
  location: location
  kind: 'app,linux'
  properties: {
    enabled: true
    reserved: true
    hostNameSslStates: [
      {
        name: '${webAppName}.azurewebsites.net'
        sslState: 'Disabled'
        hostType: 'Standard'
      }
      {
        name: '${webAppName}.scm.azurewebsites.net'
        sslState: 'Disabled'
        hostType: 'Repository'
      }
    ]
    serverFarmId: serverfarmID
    siteConfig: {
      linuxFxVersion: linuxFxVersion
    }
  }
}

resource existingDnsZone 'Microsoft.Network/dnsZones@2018-05-01' existing = {
  name: dnsZone
  scope: resourceGroup(platformRGName)
}

module dnsUpdate 'dns-update.bicep' = {
  name: 'update_dns'
  scope: resourceGroup(platformRGName)
  params: {
    dnsZone: existingDnsZone.name
    domainVerificationId: appservice.properties.customDomainVerificationId
    webAppName: webAppName
    subDomain: subDomain
  }
}


resource webAppHostname 'Microsoft.Web/sites/hostNameBindings@2021-03-01' = {
  parent: appservice
  name: '${webAppName}.${subDomain}.${dnsZone}'
  dependsOn: [
    dnsUpdate
  ]
  properties: {
    siteName: appservice.name
    hostNameType: 'Verified'
    sslState: 'Disabled'
    customHostNameDnsRecordType: 'CName'
  }
}

resource webAppCustomHostCertificate 'Microsoft.Web/certificates@2020-06-01' = {
  name: '${webAppName}.${subDomain}.${dnsZone}'
  // name: dnsZone
  location: location
  dependsOn: [
    webAppHostname
  ]
  properties: any({
    serverFarmId: serverfarmID
    canonicalName: '${webAppName}.${subDomain}.${dnsZone}'
  })
}

module webAppCustomHostEnable './sni-enable.bicep' = {
  name: '${deployment().name}-${webAppName}-sni-enable'
  params: {
    webAppName: appservice.name
    webAppHostname: webAppCustomHostCertificate.name
    certificateThumbprint: webAppCustomHostCertificate.properties.thumbprint
  }
}

output appFQDN string = appservice.properties.defaultHostName
