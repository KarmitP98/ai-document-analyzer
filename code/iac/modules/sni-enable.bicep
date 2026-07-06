param webAppName string
param webAppHostname string
param certificateThumbprint string

resource webAppCustomHostEnable 'Microsoft.Web/sites/hostNameBindings@2020-06-01' = {
  name: '${webAppName}/${webAppHostname}'
  properties: {
    sslState: 'SniEnabled'
    thumbprint: certificateThumbprint
  }
}
