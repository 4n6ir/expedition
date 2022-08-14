import boto3
import sys

from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_cloudwatch as _cloudwatch,
    aws_dynamodb as _dynamodb,
    aws_events as _events,
    aws_events_targets as _targets,
    aws_iam as _iam,
    aws_lambda as _lambda,
    aws_lambda_event_sources as _sources,
    aws_logs as _logs,
    aws_logs_destinations as _destinations,
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
            encryption = _s3.BucketEncryption.S3_MANAGED,
            block_public_access = _s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy = RemovalPolicy.DESTROY,
            auto_delete_objects = True,
            versioned = True
        )
    
        bucket.add_lifecycle_rule(
            expiration = Duration.days(1),
            noncurrent_version_expiration = Duration.days(42)
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
            stream = _dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
            removal_policy = RemovalPolicy.DESTROY,
            point_in_time_recovery = True
        )

        actionindex.add_global_secondary_index(
            index_name = 'actions',
            partition_key = {
                'name': 'action',
                'type': _dynamodb.AttributeType.STRING
            },
            sort_key = {
                'name': 'sk',
                'type': _dynamodb.AttributeType.STRING
            },
            projection_type = _dynamodb.ProjectionType.ALL
        )

        errorindex = _dynamodb.Table(
            self, 'errorindex',
            table_name = 'ErrorIndex',
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

        errorindex.add_global_secondary_index(
            index_name = 'errors',
            partition_key = {
                'name': 'action',
                'type': _dynamodb.AttributeType.STRING
            },
            sort_key = {
                'name': 'sk',
                'type': _dynamodb.AttributeType.STRING
            },
            projection_type = _dynamodb.ProjectionType.ALL
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
                    'dynamodb:PutItem',
                    'dynamodb:Query'
                ],
                resources = [
                    actionindex.table_arn,
                    errorindex.table_arn
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
                    's3:GetObject',
                    's3:PutObject'
                ],
                resources = [
                    bucket.bucket_arn,
                    bucket.arn_for_objects('*')
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

        role.add_to_policy(
            _iam.PolicyStatement(
                actions = [
                    'sns:Publish'
                ],
                resources = [
                    billingtopic.topic_arn,
                    operationstopic.topic_arn,
                    securitytopic.topic_arn
                ]
            )
        )

        error = _lambda.Function(
            self, 'error',
            runtime = _lambda.Runtime.PYTHON_3_9,
            code = _lambda.Code.from_asset('error'),
            handler = 'error.handler',
            role = role,
            environment = dict(
                SNS_TOPIC = operationstopic.topic_arn
            ),
            architecture = _lambda.Architecture.ARM_64,
            timeout = Duration.seconds(3),
            memory_size = 128
        )

        errormonitor = _logs.LogGroup(
            self, 'errormonitor',
            log_group_name = '/aws/lambda/'+error.function_name,
            retention = _logs.RetentionDays.ONE_DAY,
            removal_policy = RemovalPolicy.DESTROY
        )

        alarm = _lambda.Function(
            self, 'alarm',
            runtime = _lambda.Runtime.PYTHON_3_9,
            code = _lambda.Code.from_asset('alarm'),
            handler = 'alarm.handler',
            role = role,
            environment = dict(
                SNS_TOPIC = securitytopic.topic_arn
            ),
            architecture = _lambda.Architecture.ARM_64,
            timeout = Duration.seconds(3),
            memory_size = 128
        )

        alarmlogs = _logs.LogGroup(
            self, 'alarmlogs',
            log_group_name = '/aws/lambda/'+alarm.function_name,
            retention = _logs.RetentionDays.ONE_DAY,
            removal_policy = RemovalPolicy.DESTROY
        )

        alarmsub = _logs.SubscriptionFilter(
            self, 'alarmsub',
            log_group = alarmlogs,
            destination = _destinations.LambdaDestination(error),
            filter_pattern = _logs.FilterPattern.all_terms('ERROR')
        )

        alarmtime = _logs.SubscriptionFilter(
            self, 'alarmtime',
            log_group = alarmlogs,
            destination = _destinations.LambdaDestination(error),
            filter_pattern = _logs.FilterPattern.all_terms('Task','timed','out')
        )

        alarm.add_event_source(
            _sources.DynamoEventSource(
                table = actionindex,
                starting_position = _lambda.StartingPosition.LATEST
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

        startquerysub = _logs.SubscriptionFilter(
            self, 'startquerysub',
            log_group = startquerylogs,
            destination = _destinations.LambdaDestination(error),
            filter_pattern = _logs.FilterPattern.all_terms('ERROR')
        )

        startquerytime= _logs.SubscriptionFilter(
            self, 'startquerytime',
            log_group = startquerylogs,
            destination = _destinations.LambdaDestination(error),
            filter_pattern = _logs.FilterPattern.all_terms('Task','timed','out')
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

        passthrusub = _logs.SubscriptionFilter(
            self, 'passthrusub',
            log_group = passthrulogs,
            destination = _destinations.LambdaDestination(error),
            filter_pattern = _logs.FilterPattern.all_terms('ERROR')
        )

        passthrutime = _logs.SubscriptionFilter(
            self, 'passthrutime',
            log_group = passthrulogs,
            destination = _destinations.LambdaDestination(error),
            filter_pattern = _logs.FilterPattern.all_terms('Task','timed','out')
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

        batchwritersub = _logs.SubscriptionFilter(
            self, 'batchwritersub',
            log_group = batchwriterlogs,
            destination = _destinations.LambdaDestination(error),
            filter_pattern = _logs.FilterPattern.all_terms('ERROR')
        )

        batchwritertime = _logs.SubscriptionFilter(
            self, 'batchwritertime',
            log_group = batchwriterlogs,
            destination = _destinations.LambdaDestination(error),
            filter_pattern = _logs.FilterPattern.all_terms('Task','timed','out')
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

        actionevent.add_target(
            _targets.LambdaFunction(
                startquery,
                event = _events.RuleTargetInput.from_object(
                    {
                        "query": "SELECT eventSource, eventName, recipientAccountId, awsRegion, COUNT(*) AS apiCount FROM <DATA> WHERE eventTime >= '<START>' AND eventTime < '<END>' AND (errorMessage != '' OR errorCode != '') GROUP BY eventSource, eventName, recipientAccountId, awsRegion",
                        "table": "ErrorIndex"
                    }
                )
            )
        )

        report = _lambda.Function(
            self, 'report',
            runtime = _lambda.Runtime.PYTHON_3_9,
            code = _lambda.Code.from_asset('report'),
            handler = 'report.handler',
            role = role,
            environment = dict(
                BUCKET = bucket.bucket_name
            ),
            architecture = _lambda.Architecture.ARM_64,
            timeout = Duration.seconds(900),
            memory_size = 128
        )

        reportlogs = _logs.LogGroup(
            self, 'reportlogs',
            log_group_name = '/aws/lambda/'+report.function_name,
            retention = _logs.RetentionDays.ONE_DAY,
            removal_policy = RemovalPolicy.DESTROY
        )

        reportsub = _logs.SubscriptionFilter(
            self, 'reportsub',
            log_group = reportlogs,
            destination = _destinations.LambdaDestination(error),
            filter_pattern = _logs.FilterPattern.all_terms('ERROR')
        )

        reporttime = _logs.SubscriptionFilter(
            self, 'reporttime',
            log_group = reportlogs,
            destination = _destinations.LambdaDestination(error),
            filter_pattern = _logs.FilterPattern.all_terms('Task','timed','out')
        )

        reportevent = _events.Rule(
            self, 'reportevent',
            schedule = _events.Schedule.cron(
                minute = '17',
                hour = '*',
                month = '*',
                week_day = '*',
                year = '*'
            )
        )
        
        reportevent.add_target(
            _targets.LambdaFunction(
                report,
                event = _events.RuleTargetInput.from_object(
                    {
                        "folder": "actions",
                        "table": "ActionIndex"
                    }
                )
            )
        )

        reportevent.add_target(
            _targets.LambdaFunction(
                report,
                event = _events.RuleTargetInput.from_object(
                    {
                        "folder": "errors",
                        "table": "ErrorIndex"
                    }
                )
            )
        )

        widgetactions = _lambda.Function(
            self, 'widgetactions',
            runtime = _lambda.Runtime.PYTHON_3_9,
            code = _lambda.Code.from_asset('widgetactions'),
            handler = 'widgetactions.handler',
            role = role,
            environment = dict(
                BUCKET = bucket.bucket_name
            ),
            architecture = _lambda.Architecture.ARM_64,
            timeout = Duration.seconds(900),
            memory_size = 128
        )

        widgetactionslogs = _logs.LogGroup(
            self, 'widgetactionslogs',
            log_group_name = '/aws/lambda/'+widgetactions.function_name,
            retention = _logs.RetentionDays.ONE_DAY,
            removal_policy = RemovalPolicy.DESTROY
        )

        widgetactionssub = _logs.SubscriptionFilter(
            self, 'widgetactionssub',
            log_group = widgetactionslogs,
            destination = _destinations.LambdaDestination(error),
            filter_pattern = _logs.FilterPattern.all_terms('ERROR')
        )

        widgetactionstime = _logs.SubscriptionFilter(
            self, 'widgetactionstime',
            log_group = widgetactionslogs,
            destination = _destinations.LambdaDestination(error),
            filter_pattern = _logs.FilterPattern.all_terms('Task','timed','out')
        )

        dashboardactions = _cloudwatch.Dashboard(
            self, 'dashboardactions',
            dashboard_name = 'ExpeditionActions'
        )

        dashboardactions.add_widgets(
            _cloudwatch.CustomWidget(
                function_arn = widgetactions.function_arn,
                title = 'Expedition Actions'
            )
        )

        widgeterrors = _lambda.Function(
            self, 'widgeterrors',
            runtime = _lambda.Runtime.PYTHON_3_9,
            code = _lambda.Code.from_asset('widgeterrors'),
            handler = 'widgeterrors.handler',
            role = role,
            environment = dict(
                BUCKET = bucket.bucket_name
            ),
            architecture = _lambda.Architecture.ARM_64,
            timeout = Duration.seconds(900),
            memory_size = 128
        )

        widgeterrorslogs = _logs.LogGroup(
            self, 'widgeterrorslogs',
            log_group_name = '/aws/lambda/'+widgeterrors.function_name,
            retention = _logs.RetentionDays.ONE_DAY,
            removal_policy = RemovalPolicy.DESTROY
        )

        widgeterrorssub = _logs.SubscriptionFilter(
            self, 'widgeterrorssub',
            log_group = widgeterrorslogs,
            destination = _destinations.LambdaDestination(error),
            filter_pattern = _logs.FilterPattern.all_terms('ERROR')
        )

        widgeterrorstime = _logs.SubscriptionFilter(
            self, 'widgeterrorstime',
            log_group = widgeterrorslogs,
            destination = _destinations.LambdaDestination(error),
            filter_pattern = _logs.FilterPattern.all_terms('Task','timed','out')
        )

        dashboarderrors = _cloudwatch.Dashboard(
            self, 'dashboarderrors',
            dashboard_name = 'ExpeditionErrors'
        )

        dashboardactions.add_widgets(
            _cloudwatch.CustomWidget(
                function_arn = widgeterrors.function_arn,
                title = 'Expedition Errors'
            )
        )
