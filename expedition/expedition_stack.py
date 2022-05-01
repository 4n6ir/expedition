from aws_cdk import (
    Stack,
    aws_iam as _iam
)

from constructs import Construct

class ExpeditionStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

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
