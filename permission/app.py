#!/usr/bin/env python3
import os

import aws_cdk as cdk

from permission.permission_stack import PermissionStack

app = cdk.App()

PermissionStack(
    app, 'PermissionStack',
    env = cdk.Environment(
        account = os.getenv('CDK_DEFAULT_ACCOUNT'),
        region = os.getenv('CDK_DEFAULT_REGION')
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = '4n6ir'
    )
)

cdk.Tags.of(app).add('Alias','Portal')
cdk.Tags.of(app).add('Expedition','Expedition')
cdk.Tags.of(app).add('GitHub','https://github.com/jblukach/expedition/tree/main/permission')

app.synth()
