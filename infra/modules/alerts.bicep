@description('Azure region for alert resources.')
param location string

@description('Action Group name.')
param actionGroupName string

@description('Scheduled query alert rule name.')
param alertRuleName string

@description('Log Analytics workspace resource ID.')
param workspaceResourceId string

@description('Email address for alert notifications.')
param alertEmailAddress string

@description('Tags applied to resources.')
param tags object = {}

resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: actionGroupName
  location: 'global'
  tags: tags
  properties: {
    enabled: true
    groupShortName: take(replace(actionGroupName, '-', ''), 12)
    emailReceivers: [
      {
        name: 'primaryEmail'
        emailAddress: alertEmailAddress
        useCommonAlertSchema: true
      }
    ]
  }
}

resource exceptionAlert 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
  name: alertRuleName
  location: location
  tags: tags
  properties: {
    description: 'Triggers when exceptions are detected in the last 24 hours.'
    enabled: true
    severity: 1
    scopes: [
      workspaceResourceId
    ]
    evaluationFrequency: 'PT1H'
    windowSize: 'P1D'
    criteria: {
      allOf: [
        {
          query: 'exceptions | count'
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

output actionGroupName string = actionGroup.name
output actionGroupId string = actionGroup.id
output alertRuleName string = exceptionAlert.name
output alertRuleId string = exceptionAlert.id
