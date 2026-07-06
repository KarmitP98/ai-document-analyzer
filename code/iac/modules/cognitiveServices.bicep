param ocrName string
param nerName string
param location string
param ocrSku string = 'S1'
param nerSku string = 'S'
param kvtName string

resource ocr 'Microsoft.CognitiveServices/accounts@2022-03-01' = {
  name: ocrName
  location: location
  sku: {
    name: ocrSku
  }
  kind: 'ComputerVision'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: ocrName
    networkAcls: {
      defaultAction: 'Allow'
      virtualNetworkRules: []
      ipRules: []
    }
    publicNetworkAccess: 'Enabled'
  }
}

resource ner 'Microsoft.CognitiveServices/accounts@2022-03-01' = {
  name: nerName
  location: location
  sku: {
    name: nerSku
  }
  kind: 'TextAnalytics'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: nerName
    networkAcls: {
      defaultAction: 'Allow'
      virtualNetworkRules: []
      ipRules: []
    }
    publicNetworkAccess: 'Enabled'
  }
}

resource ocr_key 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  name: '${kvtName}/${ocr.name}-key'
  properties: {
    contentType: 'key1 for OCR'
    value: ocr.listKeys().key1
    attributes: {
      enabled: true
    }
  }
}

resource ner_key 'Microsoft.KeyVault/vaults/secrets@2021-11-01-preview' = {
  name: '${kvtName}/${ner.name}-key'
  properties: {
    contentType: 'key1 for NER'
    value: ner.listKeys().key1
    attributes: {
      enabled: true
    }
  }
}


// Retrieve resource property
output ocrMIobjectID string = ocr.identity.principalId
output nerMIobjectID string = ner.identity.principalId
output ocrKeyvaultRef string = ocr_key.properties.secretUriWithVersion
output nerKeyvaultRef string = ner_key.properties.secretUriWithVersion


