import boto3
import sys

from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_dynamodb as _dynamodb,
    aws_events as _events,
    aws_events_targets as _targets,
    aws_iam as _iam,
    aws_lambda as _lambda,
    aws_logs as _logs,
    aws_s3 as _s3,
    aws_sns as _sns,
    aws_sns_subscriptions as _subs,
    aws_ssm as _ssm,
    aws_stepfunctions as _sfn,
    aws_stepfunctions_tasks as _tasks
)

from constructs import Construct

class ExpeditionStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        account = Stack.of(self).account
        region = Stack.of(self).region
        bucket_name = 'expedition-'+account+'-'+region

        try:
            client = boto3.client('account')
            billing = client.get_alternate_contact(
                AlternateContactType='BILLING'
            )
            operations = client.get_alternate_contact(
                AlternateContactType='OPERATIONS'
            )
            security = client.get_alternate_contact(
                AlternateContactType='SECURITY'
            )
        except:
            print('Missing IAM Permission --> account:GetAlternateContact')
            sys.exit(1)
            pass

        billingtopic = _sns.Topic(
            self, 'billingtopic'
        )

        billingtopic.add_subscription(
            _subs.EmailSubscription(billing['AlternateContact']['EmailAddress'])
        )

        operationstopic = _sns.Topic(
            self, 'operationstopic'
        )

        operationstopic.add_subscription(
            _subs.EmailSubscription(operations['AlternateContact']['EmailAddress'])
        )

        securitytopic = _sns.Topic(
            self, 'securitytopic'
        )

        securitytopic.add_subscription(
            _subs.EmailSubscription(security['AlternateContact']['EmailAddress'])
        )

        bucket = _s3.Bucket(
            self, 'bucket',
            bucket_name = bucket_name,
            encryption = _s3.BucketEncryption.KMS_MANAGED,
            block_public_access = _s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy = RemovalPolicy.DESTROY,
            auto_delete_objects = True,
            versioned = True
        )
    
        bucket.add_lifecycle_rule(
            expiration = Duration.days(1),
            noncurrent_version_expiration = Duration.days(1)
        )

        actionindex = _dynamodb.Table(
            self, 'actionindex',
            table_name = 'ActionIndex',
            partition_key = {
                'name': 'pk',
                'type': _dynamodb.AttributeType.STRING
            },
            sort_key = {
                'name': 'sk',
                'type': _dynamodb.AttributeType.STRING
            },
            billing_mode = _dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy = RemovalPolicy.DESTROY,
            point_in_time_recovery = True
        )

        role = _iam.Role(
            self, 'role',
            assumed_by = _iam.ServicePrincipal(
                'lambda.amazonaws.com'
            )
        )

        role.add_managed_policy(
            _iam.ManagedPolicy.from_aws_managed_policy_name(
                'service-role/AWSLambdaBasicExecutionRole'
            )
        )

        role.add_to_policy(
            _iam.PolicyStatement(
                actions = [
                    'dynamodb:PutItem'
                ],
                resources = [
                    actionindex.table_arn
                ]
            )
        )

        role.add_to_policy(
            _iam.PolicyStatement(
                actions = [
                    'kms:Decrypt'
                ],
                resources = [
                    'arn:aws:kms:'+region+':*:key/*'
                ]
            )
        )

        role.add_to_policy(
            _iam.PolicyStatement(
                actions = [
                    'organizations:DescribeOrganization'
                ],
                resources = [
                    '*'
                ]
            )
        )

        role.add_to_policy(
            _iam.PolicyStatement(
                actions = [
                    'ssm:GetParameter'
                ],
                resources = [
                    '*'
                ]
            )
        )

        role.add_to_policy(
            _iam.PolicyStatement(
                actions = [
                    'states:StartExecution'
                ],
                resources = [
                    '*'
                ]
            )
        )

        role.add_to_policy(
            _iam.PolicyStatement(
                actions = [
                    'secretsmanager:GetSecretValue'
                ],
                resources = [
                    'arn:aws:secretsmanager:'+region+':*:secret:expedition*'
                ]
            )
        )

        role.add_to_policy(
            _iam.PolicyStatement(
                actions = [
                    'sts:AssumeRole'
                ],
                resources = [
                    'arn:aws:iam::*:role/expedition'
                ]
            )
        )

        startquery = _lambda.Function(
            self, 'startquery',
            runtime = _lambda.Runtime.PYTHON_3_9,
            code = _lambda.Code.from_asset('startquery'),
            architecture = _lambda.Architecture.ARM_64,
            timeout = Duration.seconds(900),
            handler = 'startquery.handler',
            environment = dict(
                REGION = region,
                STATE = '/expedition/state'
            ),
            memory_size = 128,
            role = role
        )
        
        startquerylogs = _logs.LogGroup(
            self, 'startquerylogs',
            log_group_name = '/aws/lambda/'+startquery.function_name,
            retention = _logs.RetentionDays.INFINITE,
            removal_policy = RemovalPolicy.DESTROY
        )

        passthru = _lambda.Function(
            self, 'passthru',
            runtime = _lambda.Runtime.PYTHON_3_9,
            code = _lambda.Code.from_asset('passthru'),
            architecture = _lambda.Architecture.ARM_64,
            timeout = Duration.seconds(3),
            handler = 'passthru.handler',
            memory_size = 128,
            role = role
        )
        
        passthrulogs = _logs.LogGroup(
            self, 'passthrulogs',
            log_group_name = '/aws/lambda/'+passthru.function_name,
            retention = _logs.RetentionDays.ONE_DAY,
            removal_policy = RemovalPolicy.DESTROY
        )

        batchwriter = _lambda.Function(
            self, 'batchwriter',
            runtime = _lambda.Runtime.PYTHON_3_9,
            code = _lambda.Code.from_asset('batchwriter'),
            architecture = _lambda.Architecture.ARM_64,
            timeout = Duration.seconds(900),
            handler = 'batchwriter.handler',
            memory_size = 128,
            role = role
        )
        
        batchwriterlogs = _logs.LogGroup(
            self, 'batchwriterlogs',
            log_group_name = '/aws/lambda/'+batchwriter.function_name,
            retention = _logs.RetentionDays.ONE_DAY,
            removal_policy = RemovalPolicy.DESTROY
        )

        initial = _tasks.LambdaInvoke(
            self, 'initial',
            lambda_function = passthru,
            output_path = '$.Payload',
        )

        batch = _tasks.LambdaInvoke(
            self, 'batch',
            lambda_function = batchwriter,
            output_path = '$.Payload',
        )

        failed = _sfn.Fail(
            self, 'failed',
            cause = 'Failed',
            error = 'FAILED'
        )

        succeed = _sfn.Succeed(
            self, 'succeeded',
            comment = 'SUCCEEDED'
        )

        definition = initial.next(batch) \
            .next(_sfn.Choice(self, 'Completed?')
                .when(_sfn.Condition.string_equals('$.status', 'FAILED'), failed)
                .when(_sfn.Condition.string_equals('$.status', 'SUCCEEDED'), succeed)
                .otherwise(batch)
            )
            
        statelogs = _logs.LogGroup(
            self, 'statelogs',
            log_group_name = '/aws/state/expedition',
            retention = _logs.RetentionDays.ONE_DAY,
            removal_policy = RemovalPolicy.DESTROY
        )
            
        state = _sfn.StateMachine(
            self, 'state',
            state_machine_name = 'expedition',
            definition = definition,
            logs = _sfn.LogOptions(
                destination = statelogs,
                level = _sfn.LogLevel.ALL
            ),
            timeout = Duration.minutes(30)
        )

        parameter = _ssm.StringParameter(
            self, 'parameter',
            description = 'Expedition State',
            parameter_name = '/expedition/state',
            string_value = state.state_machine_arn,
            tier = _ssm.ParameterTier.STANDARD
        )

        actionevent = _events.Rule(
            self, 'actionevent',
            schedule = _events.Schedule.cron(
                minute = '1',
                hour = '*',
                month = '*',
                week_day = '*',
                year = '*'
            )
        )
        
        actionevent.add_target(
            _targets.LambdaFunction(
                startquery,
                event = _events.RuleTargetInput.from_object(
                    {
                        "query": "SELECT eventSource, eventName, recipientAccountId, awsRegion, COUNT(*) AS apiCount FROM <DATA> WHERE eventTime >= '<START>' AND eventTime < '<END>' GROUP BY eventSource, eventName, recipientAccountId, awsRegion",
                        "table": "ActionIndex"
                    }
                )
            )
        )
