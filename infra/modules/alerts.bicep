@description('Deployment location.')
param location string = resourceGroup().location

@description('Resource ID of the Application Insights component.')
param applicationInsightsResourceId string

@description('Name of the Application Insights component.')
param applicationInsightsName string

@description('Name of the alert action group.')
param actionGroupName string = 'ag-alerts-${uniqueString(resourceGroup().id)}'

@description('Email address used by the alert action group.')
param alertEmailAddress string = 'rciapala@microsoft.com'

@description('Resource tags.')
param tags object = {}

resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: actionGroupName
  location: 'global'
  tags: tags
  properties: {
    groupShortName: 'rciapala'
    enabled: true
    emailReceivers: [
      {
        name: 'rciapala'
        emailAddress: alertEmailAddress
        useCommonAlertSchema: true
      }
    ]
  }
}

resource executionFailureAlert 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
  name: '${applicationInsightsName}-execution-failure-alert'
  location: location
  tags: tags
  properties: {
    description: 'Alerts when function execution failures are detected in Application Insights.'
    displayName: '${applicationInsightsName} execution failures'
    enabled: true
    severity: 2
    evaluationFrequency: 'PT5M'
    windowSize: 'PT1H'
    scopes: [
      applicationInsightsResourceId
    ]
    criteria: {
      allOf: [
        {
          query: 'exceptions | where timestamp >= ago(1h) | summarize failureCount = count()'
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    autoMitigate: true
    actions: {
      actionGroups: [
        actionGroup.id
      ]
    }
  }
}

resource durationAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${applicationInsightsName}-duration-alert'
  location: 'global'
  tags: tags
  properties: {
    description: 'Alerts when function execution duration exceeds 90 seconds.'
    severity: 2
    enabled: true
    scopes: [
      applicationInsightsResourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'ExecutionDurationOver90Seconds'
          metricNamespace: 'microsoft.insights/components'
          metricName: 'requests/duration'
          operator: 'GreaterThan'
          threshold: 90000
          timeAggregation: 'Average'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
    autoMitigate: true
  }
}

resource dataQualityAlert 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
  name: '${applicationInsightsName}-player-count-data-quality-alert'
  location: location
  tags: tags
  properties: {
    description: 'Alerts when player_count_returned custom metric is outside the expected [24, 40] range.'
    displayName: '${applicationInsightsName} player count data quality'
    enabled: true
    severity: 2
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    scopes: [
      applicationInsightsResourceId
    ]
    criteria: {
      allOf: [
        {
          query: 'customMetrics | where name == "player_count_returned" and timestamp >= ago(5m) | summarize minPlayerCount = min(value), maxPlayerCount = max(value) | where minPlayerCount < 24 or maxPlayerCount > 40'
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    autoMitigate: true
    actions: {
      actionGroups: [
        actionGroup.id
      ]
    }
  }
}

output actionGroupId string = actionGroup.id
output executionFailureAlertId string = executionFailureAlert.id
output durationAlertId string = durationAlert.id
output dataQualityAlertId string = dataQualityAlert.id
