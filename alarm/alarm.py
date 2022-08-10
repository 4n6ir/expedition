import boto3
import json
import os

def handler(event, context):
    
    actions = []
    actions.append('cloudtrail:DeleteEventDataStore')
    actions.append('cloudtrail:DeleteTrail')
    actions.append('cloudtrail:StopLogging')
    actions.append('cloudtrail:UpdateEventDataStore')
    actions.append('cloudtrail:UpdateTrail')
    actions.append('config:DeleteDeliveryChannel')
    actions.append('config:StopConfigurationRecorder')
    actions.append('ec2:CreateInstanceExportTask')
    actions.append('ec2:DescribeInstanceAttribute')
    actions.append('ec2:DisableEbsEncryptionByDefault')
    actions.append('ec2:ModifyInstanceAttribute')
    actions.append('ec2:ModifySnapshotAttribute')
    actions.append('ecs:DescribeTaskDefinition')
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
    actions.append('iam:CreateAccessKey')
    actions.append('iam:UpdateLoginProfile')
    actions.append('iam:UpdateSAMLProvider')
    actions.append('lambda:CreateFunction')
    actions.append('lambda:UpdateFunctionConfiguration')
    actions.append('macie:DisableMacie')
    actions.append('macie2:DisableMacie')
    actions.append('rds:ModifyDBInstance')
    actions.append('rds:RestoreDBInstanceFromDBSnapshot')
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
    actions.append('sts:AssumeRoleWithSAML')
    actions.append('sts:GetCallerIdentity')
    actions.append('sts:GetSessionToken')

    if event['Records'][0]['dynamodb']['NewImage']['action']['S'] in actions:

        client = boto3.client('sns')

        response = client.publish(
            TopicArn = os.environ['SNS_TOPIC'],
            Subject = 'Expedition Alarm - '+str(event['Records'][0]['dynamodb']['NewImage']['action']['S']),
            Message = str(event['Records'][0]['dynamodb']['NewImage'])
        )

    return {
        'statusCode': 200,
        'body': json.dumps('Expedition Alarm')
    }