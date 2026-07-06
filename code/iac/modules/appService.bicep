param aspName string
param location string
param aspSku string = 'P2V2'
param aspTier string = 'PremiumV2'
param autoscale object

resource asp 'Microsoft.Web/serverfarms@2021-03-01' = {
  name: aspName
  location: location
  properties: {
    reserved: true
  }
  sku: {
    name: aspSku
    tier: aspTier
  }
  kind: 'linux'
}

resource asp_autoscale 'Microsoft.Insights/autoscalesettings@2022-10-01' = {
  name: '${aspName}-autoscale'
  location: location
  properties: {
    profiles: [
      {
        name: 'DefaultAutoscaleProfile'
        capacity: {
          minimum: autoscale.minimumCapacity
          maximum: autoscale.maximumCapacity
          default: autoscale.defaultCapacity
        }
        rules: [
          {
            metricTrigger: {
              metricName: 'CpuPercentage'
              metricResourceUri: asp.id
              timeGrain: 'PT1M'
              statistic: 'Max'
              timeWindow: 'PT5M'
              timeAggregation: 'Maximum'
              operator: 'GreaterThanOrEqual'
              threshold: autoscale.threshold
            }
            scaleAction: {
              direction: 'Increase'
              type: 'ChangeCount'
              value: '2'
              cooldown: 'PT5M'
            }
          }
          {
            metricTrigger: {
              metricName: 'CpuPercentage'
              metricResourceUri: asp.id
              timeGrain: 'PT1M'
              statistic: 'Max'
              timeWindow: 'PT5M'
              timeAggregation: 'Maximum'
              operator: 'LessThan'
              threshold: autoscale.threshold
            }
            scaleAction: {
              direction: 'Decrease'
              type: 'ChangeCount'
              value: '2'
              cooldown: 'PT5M'
            }
          }
        ]
      }
    ]
    enabled: true
    targetResourceUri: asp.id
  }
}

output planId string = asp.id
