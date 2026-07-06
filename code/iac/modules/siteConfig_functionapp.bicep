param functionAppName string
param acrName string
param storagename string
param ocrname string
param taname string
param appInsightsKey string
param ocrKeyvaultRef string
param nerKeyvaultRef string
param stgKeyvaultRef string
param stgKeyvaultKeyRef string

var container_url = '${acrName}.azurecr.io'
var container_name = 'chromadiverse-app'
var ocr_url = 'https://${ocrname}.cognitiveservices.azure.com/'
var ta_url = 'https://${taname}.cognitiveservices.azure.com/'
var blob_url = 'https://${storagename}.blob.core.windows.net/'
var table_url = 'https://${storagename}.table.core.windows.net/'

resource functionapp 'Microsoft.Web/sites@2021-03-01' existing = {
  name: functionAppName
}

resource functionappsettings 'Microsoft.Web/sites/config@2021-03-01' = {
  name: 'web'
  kind: 'string'
  parent: functionapp
  properties: {
    appSettings: [
      {
        name: 'AzureWebJobsStorage'
        value: '@Microsoft.KeyVault(SecretUri=${stgKeyvaultRef})'
      }
      {
        name: 'WEBSITE_ENABLE_SYNC_UPDATE_SITE'
        value: 'true'
      }
      {
        name: 'FUNCTIONS_EXTENSION_VERSION'
        value: '~4'
      }
      {
        name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
        value: 'false'
      }
      {
        name: 'FUNCTION_APP_EDIT_MODE'
        value: 'readOnly'
      }
      {
        name: 'BlobStorageAccountName'
        value: storagename
      }
      {
        name: 'STORAGE_CONNECTION_STRING'
        value: '@Microsoft.KeyVault(SecretUri=${stgKeyvaultRef})'
      }
      {
        name: 'DOCKER_REGISTRY_SERVER_USERNAME'
        value: acrName
      }
      {
        name: 'DOCKER_CUSTOM_IMAGE_NAME'
        value: '${container_url}/${container_name}:latest'
      }
      {
        name: 'DOCKER_ENABLE_CI'
        value: 'true'
      }
      {
        name: 'DOCKER_REGISTRY_SERVER_URL'
        value: 'https://${container_url}'
      }
      {
        name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
        value: appInsightsKey
      }
      {
        name: 'CV_ENDPOINT'
        value: ocr_url
      }
      {
        name: 'CV_KEY'
        value: '@Microsoft.KeyVault(SecretUri=${ocrKeyvaultRef})'
      }
      {
        name: 'TA_ENDPOINT'
        value: ta_url
      }
      {
        name: 'TA_KEY'
        value: '@Microsoft.KeyVault(SecretUri=${nerKeyvaultRef})'
      }
      {
        name: 'BlobStorageAccountURL'
        value: blob_url
      }
      {
        name: 'TableStorageAccountURL'
        value: table_url
      }
      {
        name: 'FUNCTIONS_WORKER_RUNTIME'
        value: 'python'
      }
      {
        name: 'BlobStorageAccountKey'
        value: '@Microsoft.KeyVault(SecretUri=${stgKeyvaultKeyRef})'
      }
    ]
    connectionStrings: [
      {
        connectionString: '@Microsoft.KeyVault(SecretUri=${stgKeyvaultRef})'
        name: 'STORAGE_CONNECTION_STRING'
        type: 'Custom'
      }
    ]
  }
}
