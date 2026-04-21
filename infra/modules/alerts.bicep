param location string
param tags object = {}
param functionAppName string
param logAnalyticsWorkspaceId string
param alertEmailAddress string
param actionGroupName string = 'ag-function-alerts'
param actionGroupShortName string = 'funcalerts'

resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: actionGroupName
  location: 'Global'
  tags: tags
  properties: {
    enabled: true
    groupShortName: take(actionGroupShortName, 12)
    emailReceivers: [
      {
        name: 'rciapala-email'
        emailAddress: alertEmailAddress
        useCommonAlertSchema: true
      }
    ]
  }
}

resource executionFailureAlert 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
  name: 'alert-${functionAppName}-execution-failure-count'
  location: location
  tags: tags
  kind: 'LogAlert'
  properties: {
    displayName: 'Function execution failures > 0 (1h)'
    description: 'Fires when function execution failure count is greater than zero in a 1-hour window.'
    severity: 2
    enabled: true
    evaluationFrequency: 'PT5M'
    windowSize: 'PT1H'
    scopes: [
      logAnalyticsWorkspaceId
    ]
    targetResourceTypes: [
      'microsoft.operationalinsights/workspaces'
    ]
    criteria: {
      allOf: [
        {
          query: 'requests | where cloud_RoleName =~ "${functionAppName}" | where success == false | summarize failureCount = count()'
          timeAggregation: 'Total'
          metricMeasureColumn: 'failureCount'
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

resource executionDurationAlert 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
  name: 'alert-${functionAppName}-execution-duration'
  location: location
  tags: tags
  kind: 'LogAlert'
  properties: {
    displayName: 'Function execution duration > 90s'
    description: 'Fires when max function execution duration is greater than 90 seconds.'
    severity: 2
    enabled: true
    evaluationFrequency: 'PT5M'
    windowSize: 'PT1H'
    scopes: [
      logAnalyticsWorkspaceId
    ]
    targetResourceTypes: [
      'microsoft.operationalinsights/workspaces'
    ]
    criteria: {
      allOf: [
        {
          query: 'requests | where cloud_RoleName =~ "${functionAppName}" | summarize maxDurationSeconds = max(duration / 1s)'
          timeAggregation: 'Maximum'
          metricMeasureColumn: 'maxDurationSeconds'
          operator: 'GreaterThan'
          threshold: 90
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

resource playerCountOutOfRangeAlert 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
  name: 'alert-${functionAppName}-player-count-out-of-range'
  location: location
  tags: tags
  kind: 'LogAlert'
  properties: {
    displayName: 'Custom metric player_count_returned out of range'
    description: 'Fires when custom metric player_count_returned is lower than 24 or higher than 40.'
    severity: 2
    enabled: true
    evaluationFrequency: 'PT5M'
    windowSize: 'PT1H'
    scopes: [
      logAnalyticsWorkspaceId
    ]
    targetResourceTypes: [
      'microsoft.operationalinsights/workspaces'
    ]
    criteria: {
      allOf: [
        {
          query: 'customMetrics | where cloud_RoleName =~ "${functionAppName}" | where name == "player_count_returned" | where value < 24 or value > 40 | summarize outOfRangeCount = count()'
          timeAggregation: 'Total'
          metricMeasureColumn: 'outOfRangeCount'
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
output executionDurationAlertId string = executionDurationAlert.id
output playerCountOutOfRangeAlertId string = playerCountOutOfRangeAlert.id
