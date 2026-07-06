param dnsZone string
param location string = resourceGroup().location

resource publicDnsZone 'Microsoft.Network/dnsZones@2018-05-01' = {
  name: dnsZone
  location: location
}
