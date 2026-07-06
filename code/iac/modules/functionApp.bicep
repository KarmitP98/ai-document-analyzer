param functionAppName string
param location string
param serverfarmID string
param acrName string

var container_url = '${acrName}.azurecr.io'

resource functionApp 'Microsoft.Web/sites@2021-03-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    enabled: true
    reserved: true
    serverFarmId: serverfarmID
    siteConfig: {
      linuxFxVersion: 'DOCKER|${container_url}/chromadiverse-app:latest'
      acrUseManagedIdentityCreds: true
    }
  }
}

resource name_azurewebsites_net 'Microsoft.Web/sites/hostNameBindings@2021-03-01' = {
  parent: functionApp
  name: '${functionAppName}.azurewebsites.net'
  properties: {
    hostNameType: 'Verified'
  }
}

output fxnMIobjectID string = functionApp.identity.principalId
