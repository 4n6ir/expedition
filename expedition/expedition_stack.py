from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_iam as _iam,
    aws_lambda as _lambda,
    aws_logs as _logs
)

from constructs import Construct

class ExpeditionStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        region = Stack.of(self).region

        role = _iam.Role(
            self, 'role',
            assumed_by = _iam.ServicePrincipal(
                'lambda.amazonaws.com'
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
                    'kms:Decrypt'
                ],
                resources = [
                    'arn:aws:kms:'+region+':*:key/*'
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
                REGION = region
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
