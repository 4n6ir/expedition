#!/usr/bin/env python3
import os

import aws_cdk as cdk

from expedition.expedition_stack import ExpeditionStack

app = cdk.App()

ExpeditionStack(
    app, 'ExpeditionStack',
    env = cdk.Environment(
        account = os.getenv('CDK_DEFAULT_ACCOUNT'),
        region = os.getenv('CDK_DEFAULT_REGION')
    ),
    synthesizer = cdk.DefaultStackSynthesizer(
        qualifier = '4n6ir'
    )
)

cdk.Tags.of(app).add('Alias','Athena')
cdk.Tags.of(app).add('GitHub','https://github.com/jblukach/expedition')

app.synth()
