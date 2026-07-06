@description('Deployment location')
param location string = resourceGroup().location

@description('Azure Application Gateway v2 Name.')
param name string

@description('Subnet Resource Id.')
param subnetId string

@description('The name of the app service to be protected')
param appServiceName string

@description('The azurewebsite.net FQDN for the app service')
param appFQDN string

@description('The base64 encoded data from a .pfx cert')
@secure()
param listenerCert string

@description('Firewall Mode.  Default:  Prevention')
@allowed([
  'Detection'
  'Prevention'
])
param firewallMode string = 'Prevention'

param userAssignedID string

param dnsZone string
param subDomain string

@description('OWASP Rule Set Version.  Default: 3.0')
@allowed([
  '3.2'
  '3.1'
  '3.0'
  '2.2.9'
])
param owaspRuleSetVersion string = '3.2'

@description('SSL Predefined Policy.  Default: AppGwSslPolicy20170401')
@allowed([
  'AppGwSslPolicy20150501'
  'AppGwSslPolicy20170401'
  'AppGwSslPolicy20170401S'
])
param sslPredefinedPolicyName string = 'AppGwSslPolicy20170401'

@description('Enable HTTP 2.  Default: true')
param enableHttp2 bool = true

resource appgwPublicIp 'Microsoft.Network/publicIPAddresses@2020-06-01' = {
  name: '${name}-pip1'
  location: location
  sku: {
    name: 'Standard'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
  }
}

resource appgw 'Microsoft.Network/applicationGateways@2020-07-01' = {
  name: name
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedID}': {}
    }
  }
  properties: {
    sku: {
      name: 'WAF_v2'
      tier: 'WAF_v2'
      capacity: 1
    }
    sslPolicy: {
      policyType: 'Predefined'
      policyName: sslPredefinedPolicyName
    }
    gatewayIPConfigurations: [
      {
        properties: {
          subnet: {
            id: subnetId
          }
        }
        name: 'gatewayIpConfig'
      }
    ]
    sslCertificates: [
      {
        name: 'STAR_mnp-ai_ca'
        properties: {
          data: listenerCert
        }
      }
    ]
    webApplicationFirewallConfiguration: {
      enabled: true
      firewallMode: firewallMode
      ruleSetType: 'OWASP'
      ruleSetVersion: owaspRuleSetVersion
      requestBodyCheck: true
    }
    enableHttp2: enableHttp2
    frontendIPConfigurations: [
      {
        name: 'frontendPublicIpConfig'
        properties: {
          publicIPAddress: {
            id: appgwPublicIp.id
          }
        }
      }
    ]
    frontendPorts: [
      {
        name: 'port_80'
        properties: {
          port: 80
        }
      }
      {
        name: 'port_443'
        properties: {
          port: 443
        }
      }
    ]
    backendAddressPools: [
      {
        name: appServiceName
        properties: {
          backendAddresses: [
            {
              fqdn: appFQDN
            }
          ]
        }
      }
    ]
    backendHttpSettingsCollection: [
      {
        name: '${appServiceName}_backendSettings'
        properties: {
          port: 443
          protocol: 'Https'
          cookieBasedAffinity: 'Disabled'
          pickHostNameFromBackendAddress: true
          affinityCookieName: 'ApplicationGatewayAffinity'
          requestTimeout: 20
          probe: {
            id: resourceId('Microsoft.Network/applicationGateways/probes', name, '${appServiceName}_probe')
          }
        }
      }
    ]
    httpListeners: [
      {
        name: '${appServiceName}_listeners_443'
        properties: {
          frontendIPConfiguration: {
            id: resourceId('Microsoft.Network/applicationGateways/frontendIPConfigurations', name, 'frontendPublicIpConfig')
          }
          frontendPort: {
            id: resourceId('Microsoft.Network/applicationGateways/frontendPorts', name, 'port_443')
          }
          protocol: 'Https'
          sslCertificate: {
            id: resourceId('Microsoft.Network/applicationGateways/sslCertificates', name, 'STAR_mnp-ai_ca')
          }
          hostNames: []
          requireServerNameIndication: false
        }
      }
      {
        name: '${appServiceName}_listeners_80'
        properties: {
          frontendIPConfiguration: {
            id: resourceId('Microsoft.Network/applicationGateways/frontendIPConfigurations', name, 'frontendPublicIpConfig')
          }
          frontendPort: {
            id: resourceId('Microsoft.Network/applicationGateways/frontendPorts', name, 'port_80')
          }
          protocol: 'Http'
          hostNames: []
          requireServerNameIndication: false
        }
      }
    ]
    requestRoutingRules: [
      {
        name: '${appServiceName}_rules_443'
        properties: {
          ruleType: 'Basic'
          priority: 200
          httpListener: {
            id: resourceId('Microsoft.Network/applicationGateways/httpListeners', name, '${appServiceName}_listeners_443')
          }
          backendAddressPool: {
            id: resourceId('Microsoft.Network/applicationGateways/backendAddressPools', name, '${appServiceName}')
          }
          backendHttpSettings: {
            id: resourceId('Microsoft.Network/applicationGateways/backendHttpSettingsCollection', name, '${appServiceName}_backendSettings')
          }
        }
      }
      {
        name: '${appServiceName}_rules_80'
        properties: {
          ruleType: 'Basic'
          priority: 300
          httpListener: {
            id: resourceId('Microsoft.Network/applicationGateways/httpListeners', name, '${appServiceName}_listeners_80')
          }
          redirectConfiguration: {
            id: resourceId('Microsoft.Network/applicationGateways/redirectConfigurations', name, '${appServiceName}_redirect_80_443')
          }
        }
      }
    ]
    probes: [
      {
        name: '${appServiceName}_probe'
        properties: {
          protocol: 'Https'
          host: appFQDN
          path: '/'
          interval: 30
          timeout: 30
          unhealthyThreshold: 3
          pickHostNameFromBackendHttpSettings: false
          minServers: 0
          match: {}
        }
      }
    ]
    redirectConfigurations: [
      {
        name: '${appServiceName}_redirect_80_443'
        properties: {
          redirectType: 'Permanent'
          targetListener: {
            id: resourceId('Microsoft.Network/applicationGateways/httpListeners', name, '${appServiceName}_listeners_443')
          }
          includePath: true
          includeQueryString: true
          requestRoutingRules: [
            {
              id: resourceId('Microsoft.Network/applicationGateways/requestRoutingRules', name, '${appServiceName}_rules_80')
            }
          ]
        }
      }
    ]
  }
  zones: [
    '1'
    '2'
    '3'
  ]
}

resource dnsUpdateAGW 'Microsoft.Network/dnsZones/A@2018-05-01' = {
  name: '${dnsZone}/${subDomain}'
  dependsOn: [
    appgw
  ]
  properties: {
    TTL: 3600
    ARecords: [
      {
        ipv4Address: appgwPublicIp.properties.ipAddress
      }
    ]
  }
}

output agwPublicIp string = appgwPublicIp.properties.ipAddress
