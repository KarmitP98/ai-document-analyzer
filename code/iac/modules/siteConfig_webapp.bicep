param webAppName string
param agwPublicIp string
param storageName string
param functionName string

resource webApp 'Microsoft.Web/sites@2021-03-01' existing = {
  name: webAppName
}

resource webAppSettings 'Microsoft.Web/sites/config@2021-03-01' = {
  name: 'web'
  kind: 'string'
  parent: webApp
  properties: {
    ipSecurityRestrictions: [
      {
        ipAddress: '${agwPublicIp}/32'
        priority: 100
        action: 'Allow'
        name: 'AllowAppGateway'
        description: 'Only the App Gateway can access the app service'
      }
      {
        ipAddress: 'any'
        action: 'Deny'
        priority: 2147483647
        name: 'Deny all'
        description: 'Deny all access'
      }
    ]
    appSettings: [
      {
        name: 'blobStorage'
        value: storageName
      }
      {
        name: 'tableStorage'
        value: storageName
      }
      {
        name: 'functions'
        value: functionName
      }
    ]
  }
}
