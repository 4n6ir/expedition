from aws_cdk import (
    Stack,
    aws_iam as _iam
)

from constructs import Construct

class PermissionStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        role = _iam.Role(
            self, 'role',
            role_name = 'expedition',
            assumed_by = _iam.AccountPrincipal('210115648064'),
            external_ids = ['cc0c334d-9767-479e-a2c9-2768fb4ab16a']
        )

        role.add_to_policy(
            _iam.PolicyStatement(
                actions = [
                    'cloudtrail:StartQuery',
                    'cloudtrail:GetQueryResults'
                ],
                resources = [
                    '*'
                ]
            )
        )
