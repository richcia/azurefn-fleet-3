@description('Azure region for alert resources.')
param location string

@description('Application Insights resource ID scoped by alert rules.')
param applicationInsightsResourceId string

@description('Email address for rciapala alert notifications.')
param rciapalaEmailAddress string

@description('Optional resource tags.')
param tags object = {}

var actionGroupName = 'ag-rciapala-alerts'
var executionFailureAlertName = 'alert-function-execution-failure'
var functionDurationAlertName = 'alert-function-duration'
var playerCountLowOrHighAlertName = 'alert-player-count-out-of-range'

resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: actionGroupName
  location: 'global'
  tags: tags
  properties: {
    enabled: true
    groupShortName: 'rciapala'
    emailReceivers: [
      {
        name: 'rciapala'
        emailAddress: rciapalaEmailAddress
        useCommonAlertSchema: true
      }
    ]
  }
}

resource executionFailureAlert 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
  name: executionFailureAlertName
  location: location
  tags: tags
  properties: {
    enabled: true
    severity: 1
    displayName: 'Function execution failures > 0 in 1h'
    description: 'Fires when function execution failure count is greater than 0 over a one-hour window.'
    evaluationFrequency: 'PT5M'
    windowSize: 'PT1H'
    scopes: [
      applicationInsightsResourceId
    ]
    criteria: {
      allOf: [
        {
          query: 'union isfuzzy=true (requests\n| where timestamp >= ago(1h)\n| where success == false\n| project alertHit = 1), (AppRequests\n| where TimeGenerated >= ago(1h)\n| where Success == false\n| project alertHit = 1)'
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
    actions: {
      actionGroups: [
        actionGroup.id
      ]
    }
    autoMitigate: true
  }
}

resource functionDurationAlert 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
  name: functionDurationAlertName
  location: location
  tags: tags
  properties: {
    enabled: true
    severity: 2
    displayName: 'Function duration exceeds 90 seconds'
    description: 'Fires when a function execution duration exceeds 90 seconds.'
    evaluationFrequency: 'PT5M'
    windowSize: 'PT1H'
    scopes: [
      applicationInsightsResourceId
    ]
    criteria: {
      allOf: [
        {
          query: 'union isfuzzy=true (requests\n| where timestamp >= ago(1h)\n| where duration > time(00:01:30)\n| project alertHit = 1), (AppRequests\n| where TimeGenerated >= ago(1h)\n| where DurationMs > 90000\n| project alertHit = 1)'
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
    actions: {
      actionGroups: [
        actionGroup.id
      ]
    }
    autoMitigate: true
  }
}

resource playerCountLowOrHighAlert 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
  name: playerCountLowOrHighAlertName
  location: location
  tags: tags
  properties: {
    enabled: true
    severity: 2
    displayName: 'player_count_returned is outside expected range'
    description: 'Fires when player_count_returned is less than 24 or greater than 40.'
    evaluationFrequency: 'PT5M'
    windowSize: 'PT1H'
    scopes: [
      applicationInsightsResourceId
    ]
    criteria: {
      allOf: [
        {
          query: 'union isfuzzy=true (customMetrics\n| where timestamp >= ago(1h)\n| where name == "player_count_returned" and (value < 24 or value > 40)\n| project alertHit = 1), (AppMetrics\n| where TimeGenerated >= ago(1h)\n| where Name == "player_count_returned" and (Val < 24 or Val > 40)\n| project alertHit = 1)'
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
    actions: {
      actionGroups: [
        actionGroup.id
      ]
    }
    autoMitigate: true
  }
}

output actionGroupId string = actionGroup.id
output executionFailureAlertId string = executionFailureAlert.id
output functionDurationAlertId string = functionDurationAlert.id
output playerCountLowOrHighAlertId string = playerCountLowOrHighAlert.id
