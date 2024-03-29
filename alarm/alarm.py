import boto3
import json
import os
from datetime import datetime, timezone

def handler(event, context):

    actions = []
    actions.append('cloudshell:CreateEnvironment')
    actions.append('cloudshell:CreateSession')
    actions.append('cloudshell:DeleteEnvironment')
    actions.append('cloudshell:GetEnvironmentStatus')
    actions.append('cloudshell:GetFileDownloadUrls')
    actions.append('cloudshell:GetFileUploadUrls')
    actions.append('cloudshell:PutCredentials')
    actions.append('cloudshell:StartEnvironment')
    actions.append('cloudshell:StopEnvironment')
    actions.append('cloudtrail:DeleteEventDataStore')
    actions.append('cloudtrail:DeleteTrail')
    actions.append('cloudtrail:PutEventSelectors')
    actions.append('cloudtrail:StopLogging')
    actions.append('cloudtrail:UpdateEventDataStore')
    actions.append('cloudtrail:UpdateTrail')
    actions.append('config:DeleteDeliveryChannel')
    actions.append('config:StopConfigurationRecorder')
    actions.append('connect:CreateInstance')
    actions.append('ec2:CreateDefaultVpc')
    actions.append('ec2:CreateImage')
    actions.append('ec2:CreateInstanceExportTask')
    actions.append('ec2:CreateKeyPair')
    actions.append('ec2:DeleteFlowLogs')
    actions.append('ec2:DeleteVpc')
    actions.append('ec2:DescribeInstanceAttribute')
    actions.append('ec2:DisableEbsEncryptionByDefault')
    actions.append('ec2:GetPasswordData')
    actions.append('ec2:ModifyInstanceAttribute')
    actions.append('ec2:ModifySnapshotAttribute')
    actions.append('ec2:SharedSnapshotCopyInitiated')
    actions.append('ec2:SharedSnapshotVolumeCreated')
    actions.append('ecr:CreateRepository')
    actions.append('ecr:GetAuthorizationToken')
    #actions.append('ecs:DescribeTaskDefinition')
    actions.append('ecs:RegisterTaskDefinition')
    actions.append('ecs:RunTask')
    actions.append('eks:CreateCluster')
    actions.append('eks:DeleteCluster')
    actions.append('elasticache:AuthorizeCacheSecurityGroupEgress')
    actions.append('elasticache:AuthorizeCacheSecurityGroupIngress')
    actions.append('elasticache:CreateCacheSecurityGroup')
    actions.append('elasticache:DeleteCacheSecurityGroup')
    actions.append('elasticache:RevokeCacheSecurityGroupEgress')
    actions.append('elasticache:RevokeCacheSecurityGroupIngress')
    actions.append('elasticfilesystem:DeleteFileSystem')
    actions.append('elasticfilesystem:DeleteMountTarget')
    actions.append('glue:CreateDevEndpoint')
    actions.append('glue:DeleteDevEndpoint')
    actions.append('glue:UpdateDevEndpoint')
    actions.append('guardduty:CreateIPSet')
    actions.append('iam:AddUserToGroup')
    actions.append('iam:AttachGroupPolicy')
    actions.append('iam:AttachUserPolicy')
    actions.append('iam:ChangePassword')
    actions.append('iam:CreateAccessKey')
    actions.append('iam:CreateLoginProfile')
    actions.append('iam:CreateUser')
    actions.append('iam:CreateVirtualMFADevice')
    actions.append('iam:DeactivateMFADevice')
    actions.append('iam:DeleteAccessKey')
    actions.append('iam:DeleteUser')
    actions.append('iam:DeleteUserPolicy')
    actions.append('iam:DeleteVirtualMFADevice')
    actions.append('iam:DetachGroupPolicy')
    actions.append('iam:DetachUserPolicy')
    actions.append('iam:EnableMFADevice')
    actions.append('iam:PutUserPolicy')
    actions.append('iam:ResyncMFADevice')
    actions.append('iam:UpdateAccessKey')
    actions.append('iam:UpdateGroup')
    actions.append('iam:UpdateLoginProfile')
    actions.append('iam:UpdateSAMLProvider')
    actions.append('iam:UpdateUser')
    actions.append('kms:DisableKey')
    actions.append('kms:ScheduleKeyDeletion')
    actions.append('lambda:AddLayerVersionPermission')
    actions.append('lambda:CreateFunction')
    actions.append('lambda:GetLayerVersionPolicy')
    actions.append('lambda:PublishLayerVersion')
    actions.append('lambda:UpdateFunctionConfiguration')
    actions.append('macie:DisableMacie')
    actions.append('macie2:DisableMacie')
    actions.append('organizations:LeaveOrganization')
    actions.append('rds:ModifyDBInstance')
    actions.append('rds:RestoreDBInstanceFromDBSnapshot')
    actions.append('rolesanywhere:CreateProfile')
    actions.append('rolesanywhere:CreateTrustAnchor')
    actions.append('route53:DisableDomainTransferLock')
    actions.append('route53:TransferDomainToAnotherAwsAccount')
    actions.append('s3:PutBucketLogging')
    actions.append('s3:PutBucketWebsite')
    actions.append('s3:PutEncryptionConfiguration')
    actions.append('s3:PutLifecycleConfiguration')
    actions.append('s3:PutReplicationConfiguration')
    actions.append('s3:ReplicateObject')
    actions.append('s3:RestoreObject')
    actions.append('securityhub:BatchUpdateFindings')
    actions.append('securityhub:DeleteInsight')
    actions.append('securityhub:UpdateFindings')
    actions.append('securityhub:UpdateInsight')
    #actions.append('signin:ConsoleLogin
    actions.append('sso:AttachCustomerManagedPolicyReferenceToPermissionSet')
    actions.append('sso:AttachManagedPolicyToPermissionSet')
    actions.append('sso:CreateAccountAssignment')
    actions.append('sso:CreateInstanceAccessControlAttributeConfiguration')
    actions.append('sso:CreatePermissionSet')
    actions.append('sso:DeleteAccountAssignment')
    actions.append('sso:DeleteInlinePolicyFromPermissionSet')
    actions.append('sso:DeleteInstanceAccessControlAttributeConfiguration')
    actions.append('sso:DeletePermissionsBoundaryFromPermissionSet')
    actions.append('sso:DeletePermissionSet')
    actions.append('sso:DetachCustomerManagedPolicyReferenceFromPermissionSet')
    actions.append('sso:DetachManagedPolicyFromPermissionSet')
    actions.append('sso:ProvisionPermissionSet')
    actions.append('sso:PutInlinePolicyToPermissionSet')
    actions.append('sso:PutPermissionsBoundaryToPermissionSet')
    actions.append('sso:UpdateInstanceAccessControlAttributeConfiguration')
    actions.append('sso:UpdatePermissionSet')
    #actions.append('sts:AssumeRoleWithSAML')
    #actions.append('sts:GetCallerIdentity')
    actions.append('sts:GetFederationToken')
    actions.append('sts:GetSessionToken')

    if event['Records'][0]['dynamodb']['NewImage']['action']['S'] in actions:

        account = os.environ['ACCOUNT']
        region = os.environ['REGION']

        now = datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

        securityhub_client = boto3.client('securityhub')

        securityhub_response = securityhub_client.batch_import_findings(
            Findings = [
                {
                    "SchemaVersion": "2018-10-08",
                    "Id": region+"/"+account+"/alarm",
                    "ProductArn": "arn:aws:securityhub:"+region+":"+account+":product/"+account+"/default", 
                    "GeneratorId": "ct-alarm",
                    "AwsAccountId": account,
                    "CreatedAt": now,
                    "UpdatedAt": now,
                    "Title": "Alarm",
                    "Description": str(event['Records'][0]['dynamodb']['NewImage']),
                    "Resources": [
                        {
                            "Type": "AwsLambda",
                            "Id": "arn:aws:lambda:"+region+":"+account+":function:alarm"
                        }
                    ],
                    "FindingProviderFields": {
                        "Confidence": 100,
                        "Severity": {
                            "Label": "CRITICAL"
                        },
                        "Types": [
                            "security/ct/alarm"
                        ]
                    }
                }
            ]
        )

        print(securityhub_response)

    return {
        'statusCode': 200,
        'body': json.dumps('Expedition Alarm')
    }