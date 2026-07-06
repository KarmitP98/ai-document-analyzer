param dnsZone string
param webAppName string
param domainVerificationId string
param subDomain string


resource dnsTxt 'Microsoft.Network/dnsZones/TXT@2018-05-01' = {
  name: '${dnsZone}/asuid.${webAppName}.${subDomain}'
  properties: {
    TTL: 3600
    TXTRecords: [
      {
        value: [
          '${domainVerificationId}'
        ]
      }
    ]
  }
}

resource dnsCname 'Microsoft.Network/dnsZones/CNAME@2018-05-01' = {
  name: '${dnsZone}/${webAppName}.${subDomain}'
  properties: {
    TTL: 3600
    CNAMERecord: {
      cname: '${webAppName}.azurewebsites.net'
    }
  }
}
