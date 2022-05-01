import boto3
import json
import sys
import uuid

from aws_cdk import (
    RemovalPolicy,
    Stack,
    aws_iam as _iam,
    aws_kms as _kms,
    aws_secretsmanager as _secrets
)

from constructs import Construct

class PermissionStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        account = Stack.of(self).account
        extid = str(uuid.uuid4())
        principals = []

        try:
            client = boto3.client('organizations')
            paginator = client.get_paginator('list_accounts')
            response_iterator = paginator.paginate()
            for page in response_iterator:
                for item in page['Accounts']:
                    if item['Status'] == 'ACTIVE':
                        principals.append(str(item['Id']))
        except:
            print('Missing IAM Permission --> organizations:ListAccounts')
            sys.exit(1)
            pass
        
        composite = _iam.CompositePrincipal(
            _iam.AccountPrincipal(
                account
            )
        )
        
        for principal in principals:
            if principal != account:
                composite.add_principals(
                    _iam.AccountPrincipal(
                        principal
                    )
                )

        role = _iam.Role(
            self, 'role',
            role_name = 'expedition',
            assumed_by = composite,
            external_ids = [extid]
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

        key = _kms.Key(
            self, 'key',
            removal_policy = RemovalPolicy.DESTROY
        )

        key.add_alias('alias/expedition')

        secrets = {}
        secrets['role'] = role.role_arn
        secrets['extid'] = extid
        
        secret = _secrets.Secret(
            self, 'secret',
            secret_name = 'expedition',
            removal_policy = RemovalPolicy.DESTROY,
            generate_secret_string = _secrets.SecretStringGenerator(
                secret_string_template = json.dumps(secrets),
                generate_string_key = 'secret'
            ),
            encryption_key = key
        )

        for principal in principals:
            if principal != account:
                secret.grant_read(
                    _iam.AccountPrincipal(
                        principal
                    )    
                )
