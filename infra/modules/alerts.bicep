@description('Azure region for all resources')
param location string

@description('Resource tags')
param tags object

@description('Email address to receive alert notifications')
param alertEmailAddress string

@description('Resource ID of the Application Insights component')
param appInsightsId string

@description('Name of the Function App (used to scope alert queries)')
param functionAppName string

// ---------------------------------------------------------------------------
// Action Group (email notification)
// ---------------------------------------------------------------------------

resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: 'ag-${functionAppName}'
  location: 'global'
  tags: tags
  properties: {
    groupShortName: 'FnAlerts'
    enabled: true
    emailReceivers: [
      {
        name: 'owner'
        emailAddress: alertEmailAddress
        useCommonAlertSchema: true
      }
    ]
  }
}

// ---------------------------------------------------------------------------
// Alert 1 — Execution failure: failedRuns > 0 in a 1-hour window (severity 1)
// ---------------------------------------------------------------------------

resource failureAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: 'alert-${functionAppName}-failures'
  location: location
  tags: tags
  properties: {
    displayName: 'Function Execution Failure Alert'
    description: 'Fires when function execution failure count > 0 in a 1-hour window'
    severity: 1
    enabled: true
    evaluationFrequency: 'PT5M'
    windowSize: 'PT1H'
    scopes: [
      appInsightsId
    ]
    criteria: {
      allOf: [
        {
          query: 'requests | where cloud_RoleName == \'${functionAppName}\' and success == false | summarize FailedRuns = count()'
          timeAggregation: 'Total'
          metricMeasureColumn: 'FailedRuns'
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
    muteActionsDuration: 'PT15M'
  }
}

// ---------------------------------------------------------------------------
// Alert 2 — Duration: execution duration > 90 seconds (90 000 ms) (severity 2)
// ---------------------------------------------------------------------------

resource durationAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: 'alert-${functionAppName}-duration'
  location: location
  tags: tags
  properties: {
    displayName: 'Function Execution Duration Alert'
    description: 'Fires when maximum function execution duration exceeds 90 seconds (90 000 ms)'
    severity: 2
    enabled: true
    evaluationFrequency: 'PT5M'
    windowSize: 'PT1H'
    scopes: [
      appInsightsId
    ]
    criteria: {
      allOf: [
        {
          // When no requests arrive in the window, max(duration) returns null
          // and Azure skips the evaluation harmlessly (no false-positive fire).
          query: 'requests | where cloud_RoleName == \'${functionAppName}\' | summarize MaxDuration = max(duration)'
          timeAggregation: 'Maximum'
          metricMeasureColumn: 'MaxDuration'
          operator: 'GreaterThan'
          threshold: 90000
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
    muteActionsDuration: 'PT1H'
  }
}

// ---------------------------------------------------------------------------
// Alert 3 — Data quality: player_count_returned < 24 OR > 40 (severity 2)
// Note: The custom metric player_count_returned must be emitted at least once
//       before this alert can fire. Run a staging smoke test first.
//       Scheduled query alerts have a minimum evaluation frequency of 5 minutes.
// ---------------------------------------------------------------------------

resource dataQualityAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: 'alert-${functionAppName}-data-quality'
  location: location
  tags: tags
  properties: {
    displayName: 'Player Count Data Quality Alert'
    description: 'Fires when player_count_returned custom metric is < 24 or > 40, indicating GPT output drift'
    severity: 2
    enabled: true
    evaluationFrequency: 'PT5M'
    windowSize: 'PT1H'
    scopes: [
      appInsightsId
    ]
    criteria: {
      allOf: [
        {
          query: 'customMetrics | where cloud_RoleName == \'${functionAppName}\' | where name == \'player_count_returned\' | where value < 24 or value > 40 | summarize OutOfRangeCount = count()'
          timeAggregation: 'Total'
          metricMeasureColumn: 'OutOfRangeCount'
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
    muteActionsDuration: 'PT1H'
  }
}
