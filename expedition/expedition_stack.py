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

    ### LAMBDA LAYER ###

        if region == 'ap-northeast-1' or region == 'ap-south-1' or region == 'ap-southeast-1' or \
            region == 'ap-southeast-2' or region == 'eu-central-1' or region == 'eu-west-1' or \
            region == 'eu-west-2' or region == 'me-central-1' or region == 'us-east-1' or \
            region == 'us-east-2' or region == 'us-west-2': number = str(1)

        if region == 'af-south-1' or region == 'ap-east-1' or region == 'ap-northeast-2' or \
            region == 'ap-northeast-3' or region == 'ap-southeast-3' or region == 'ca-central-1' or \
            region == 'eu-north-1' or region == 'eu-south-1' or region == 'eu-west-3' or \
            region == 'me-south-1' or region == 'sa-east-1' or region == 'us-west-1': number = str(2)

        layer = _lambda.LayerVersion.from_layer_version_arn(
            self, 'layer',
            layer_version_arn = 'arn:aws:lambda:'+region+':070176467818:layer:getpublicip:'+number
        )

    ### STORAGE ###

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
            expiration = Duration.days(42),
            noncurrent_version_expiration = Duration.days(1)
        )

    ### DYNAMODB ###

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

        actionindex.add_global_secondary_index(
            index_name = 'addresses',
            partition_key = {
                'name': 'address',
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

        errorindex.add_global_secondary_index(
            index_name = 'addresses',
            partition_key = {
                'name': 'address',
                'type': _dynamodb.AttributeType.STRING
            },
            sort_key = {
                'name': 'sk',
                'type': _dynamodb.AttributeType.STRING
            },
            projection_type = _dynamodb.ProjectionType.ALL
        )

    ### IAM ROLE ###

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
                    'securityhub:BatchImportFindings'
                ],
                resources = [
                    'arn:aws:securityhub:'+region+':'+account+':product/'+account+'/default'
                ]
            )
        )

        role.add_to_policy(
            _iam.PolicyStatement(
                actions = [
                    'cloudtrail:GetQueryResults',
                    'cloudtrail:ListEventDataStores',
                    'cloudtrail:ListTags',
                    'cloudtrail:StartQuery'
                ],
                resources = [
                    '*'
                ]
            )
        )

    ### ERROR ###

        error = _lambda.Function.from_function_arn(
            self, 'error',
            'arn:aws:lambda:'+region+':'+account+':function:shipit-error'
        )

        timeout = _lambda.Function.from_function_arn(
            self, 'timeout',
            'arn:aws:lambda:'+region+':'+account+':function:shipit-timeout'
        )

    ### ALARM ###

        alarm = _lambda.Function(
            self, 'alarm',
            function_name = 'alarm',
            runtime = _lambda.Runtime.PYTHON_3_9,
            code = _lambda.Code.from_asset('alarm'),
            architecture = _lambda.Architecture.ARM_64,
            timeout = Duration.seconds(60),
            handler = 'alarm.handler',
            environment = dict(
                ACCOUNT = account,
                REGION = region
            ),
            memory_size = 128,
            role = role,
            layers = [
                layer
            ]
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
            destination = _destinations.LambdaDestination(timeout),
            filter_pattern = _logs.FilterPattern.all_terms('Task','timed','out')
        )

        alarm.add_event_source(
            _sources.DynamoEventSource(
                table = actionindex,
                starting_position = _lambda.StartingPosition.LATEST
            )
        )

    ### START QUERY ###

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
            role = role,
            layers = [
                layer
            ]
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
            destination = _destinations.LambdaDestination(timeout),
            filter_pattern = _logs.FilterPattern.all_terms('Task','timed','out')
        )

    ### PASS THRU ###

        passthru = _lambda.Function(
            self, 'passthru',
            runtime = _lambda.Runtime.PYTHON_3_9,
            code = _lambda.Code.from_asset('passthru'),
            architecture = _lambda.Architecture.ARM_64,
            timeout = Duration.seconds(60),
            handler = 'passthru.handler',
            memory_size = 128,
            role = role,
            layers = [
                layer
            ]
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
            destination = _destinations.LambdaDestination(timeout),
            filter_pattern = _logs.FilterPattern.all_terms('Task','timed','out')
        )

    ### BATCH WRITER ###

        batchwriter = _lambda.Function(
            self, 'batchwriter',
            runtime = _lambda.Runtime.PYTHON_3_9,
            code = _lambda.Code.from_asset('batchwriter'),
            architecture = _lambda.Architecture.ARM_64,
            timeout = Duration.seconds(900),
            handler = 'batchwriter.handler',
            memory_size = 128,
            role = role,
            layers = [
                layer
            ]
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
            destination = _destinations.LambdaDestination(timeout),
            filter_pattern = _logs.FilterPattern.all_terms('Task','timed','out')
        )

    ### STEP FUNCTION ###

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

        statesub = _logs.SubscriptionFilter(
            self, 'statesub',
            log_group = statelogs,
            destination = _destinations.LambdaDestination(error),
            filter_pattern = _logs.FilterPattern.all_terms('ERROR')
        )

        statetime = _logs.SubscriptionFilter(
            self, 'statetime',
            log_group = statelogs,
            destination = _destinations.LambdaDestination(timeout),
            filter_pattern = _logs.FilterPattern.all_terms('Task','timed','out')
        )

        state = _sfn.StateMachine(
            self, 'state',
            state_machine_name = 'expedition',
            definition = definition,
            logs = _sfn.LogOptions(
                destination = statelogs,
                level = _sfn.LogLevel.ALL
            ),
            timeout = Duration.minutes(42)
        )

        parameter = _ssm.StringParameter(
            self, 'parameter',
            description = 'Expedition State',
            parameter_name = '/expedition/state',
            string_value = state.state_machine_arn,
            tier = _ssm.ParameterTier.STANDARD
        )

    ### EVENTS ###

        actionevent = _events.Rule(
            self, 'actionevent',
            schedule = _events.Schedule.cron(
                minute = '17',
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
                        "query": "SELECT eventSource, eventName, recipientAccountId, awsRegion, sourceIPAddress, COUNT(*) AS apiCount FROM <DATA> WHERE eventTime >= '<START>' AND eventTime < '<END>' GROUP BY eventSource, eventName, recipientAccountId, awsRegion, sourceIPAddress",
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
                        "query": "SELECT eventSource, eventName, recipientAccountId, awsRegion, sourceIPAddress, COUNT(*) AS apiCount FROM <DATA> WHERE eventTime >= '<START>' AND eventTime < '<END>' AND (errorMessage != '' OR errorCode != '') GROUP BY eventSource, eventName, recipientAccountId, awsRegion, sourceIPAddress",
                        "table": "ErrorIndex"
                    }
                )
            )
        )

    ### REPORTING ###

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
            memory_size = 128,
            layers = [
                layer
            ]
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
            destination = _destinations.LambdaDestination(timeout),
            filter_pattern = _logs.FilterPattern.all_terms('Task','timed','out')
        )

        reportevent = _events.Rule(
            self, 'reportevent',
            schedule = _events.Schedule.cron(
                minute = '33',
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

    ### DASHBOARD ###

        widget = _lambda.Function(
            self, 'widget',
            runtime = _lambda.Runtime.PYTHON_3_9,
            code = _lambda.Code.from_asset('widget'),
            handler = 'widget.handler',
            role = role,
            environment = dict(
                BUCKET = bucket.bucket_name
            ),
            architecture = _lambda.Architecture.ARM_64,
            timeout = Duration.seconds(900),
            memory_size = 128,
            layers = [
                layer
            ]
        )

        widgetlogs = _logs.LogGroup(
            self, 'widgetlogs',
            log_group_name = '/aws/lambda/'+widget.function_name,
            retention = _logs.RetentionDays.ONE_DAY,
            removal_policy = RemovalPolicy.DESTROY
        )

        widgetsub = _logs.SubscriptionFilter(
            self, 'widgetsub',
            log_group = widgetlogs,
            destination = _destinations.LambdaDestination(error),
            filter_pattern = _logs.FilterPattern.all_terms('ERROR')
        )

        widgettime = _logs.SubscriptionFilter(
            self, 'widgettime',
            log_group = widgetlogs,
            destination = _destinations.LambdaDestination(timeout),
            filter_pattern = _logs.FilterPattern.all_terms('Task','timed','out')
        )

        dashboard = _cloudwatch.Dashboard(
            self, 'dashboard',
            dashboard_name = 'Expedition'
        )

        dashboard.add_widgets(
            _cloudwatch.CustomWidget(
                function_arn = widget.function_arn,
                title = 'Actions',
                params = {
                    "folder": "actions"
                },
                height = 12,
                width = 24
            )
        )

        dashboard.add_widgets(
            _cloudwatch.CustomWidget(
                function_arn = widget.function_arn,
                title = 'Errors',
                params = {
                    "folder": "errors"
                },
                height = 12,
                width = 24
            )
        )
