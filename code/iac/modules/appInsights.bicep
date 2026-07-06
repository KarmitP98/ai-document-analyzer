param appInsName string
param location string

resource applicationInsights 'microsoft.insights/components@2020-02-02' = {
  name: appInsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    RetentionInDays: 90
    IngestionMode: 'ApplicationInsights'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

output appInsightsKey string = applicationInsights.properties.InstrumentationKey
