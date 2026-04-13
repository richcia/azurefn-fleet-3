@description('Azure region for alert resources.')
param location string

@description('Name of the Action Group for alert notifications.')
param actionGroupName string

@description('Email address for alert notifications.')
param alertEmailAddress string

@description('Short name for the Action Group (max 12 chars).')
param actionGroupShortName string = 'FnAlerts'

@description('Name of the scheduled query alert rule for function exceptions.')
param alertRuleName string

@description('Resource ID of the Application Insights instance to query.')
param appInsightsId string

@description('Resource tags applied to all resources in this module.')
param tags object = {}

// ---------------------------------------------------------------------------
// Action Group — email notification
// ---------------------------------------------------------------------------

resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: actionGroupName
  location: 'global'
  tags: tags
  properties: {
    groupShortName: actionGroupShortName
    enabled: true
    emailReceivers: [
      {
        name: 'PrimaryEmailReceiver'
        emailAddress: alertEmailAddress
        useCommonAlertSchema: true
      }
    ]
  }
}

// ---------------------------------------------------------------------------
// Scheduled Query Rule — function exceptions > 0 in 24 h
// ---------------------------------------------------------------------------

resource exceptionAlertRule 'Microsoft.Insights/scheduledQueryRules@2022-06-15' = {
  name: alertRuleName
  location: location
  tags: tags
  properties: {
    description: 'Fires when Azure Function exceptions exceed 0 in a 24-hour evaluation window.'
    severity: 1
    enabled: true
    evaluationFrequency: 'PT1H'
    windowSize: 'PT24H'
    scopes: [
      appInsightsId
    ]
    criteria: {
      allOf: [
        {
          query: 'exceptions'
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
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------

@description('The resource ID of the Action Group.')
output actionGroupId string = actionGroup.id

@description('The resource ID of the exception alert rule.')
output exceptionAlertRuleId string = exceptionAlertRule.id
