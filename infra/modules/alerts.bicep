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

resource actionGroup 'microsoft.insights/actionGroups@2023-01-01' = {
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
// Scheduled Query Rule — fire when exceptions > 0 in a 24-hour window
// ---------------------------------------------------------------------------

resource exceptionAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: 'alert-${functionAppName}-exceptions'
  location: location
  tags: tags
  properties: {
    displayName: 'Function App Exceptions Alert'
    description: 'Fires when function exceptions are detected in the last 24 hours'
    severity: 2
    enabled: true
    evaluationFrequency: 'PT1H'
    windowSize: 'PT24H'
    scopes: [
      appInsightsId
    ]
    criteria: {
      allOf: [
        {
          query: 'exceptions | where cloud_RoleName == \'${functionAppName}\' | summarize Count = count()'
          timeAggregation: 'Count'
          metricMeasureColumn: 'Count'
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
  }
}
