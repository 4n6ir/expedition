# expedition-permission

Deployment to the management account requires the ```organizations:ListAccounts``` permission available in any delegated administrator account. It creates a policy statement allowing any account in the organization to consume the CloudTrail logs by granting access to the necessary KMS Key, Role Trust, and Secret. The secret contains the role arn and external id required for the assumption of permissions.

- cloudtrail:GetQueryResults
- cloudtrail:ListEventDataStores
- cloudtrail:ListTags
- cloudtrail:StartQuery
