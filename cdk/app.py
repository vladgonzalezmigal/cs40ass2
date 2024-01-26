#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk.dns_stack import DnsStack
from cdk.network_stack import NetworkStack
from cdk.data_stack import DataStack
from cdk.compute_stack import ComputeStack
from cdk.util import settings, Props

app = cdk.App()
# CdkStack(
#     app,
#     "CdkStack",
#     # If you don't specify 'env', this stack will be environment-agnostic.
#     # Account/Region-dependent features and context lookups will not work,
#     # but a single synthesized template can be deployed anywhere.
#     # Uncomment the next line to specialize this stack for the AWS Account
#     # and Region that are implied by the current CLI configuration.
#     # env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
#     # Uncomment the next line if you know exactly what Account and Region you
#     # want to deploy the stack to. */
#     # env=cdk.Environment(account='123456789012', region='us-east-1'),
#     # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
# )

props = Props()
env = cdk.Environment(account=settings.CDK_DEFAULT_ACCOUNT, region=settings.REGION)

dns_stack = DnsStack(app, f"{settings.PROJECT_NAME}-dns-stack", env=env)
props.network_hosted_zone = dns_stack.hosted_zone

network_stack = NetworkStack(
    app, f"{settings.PROJECT_NAME}-network-stack", props, env=env
)
props.network_vpc = network_stack.vpc
props.network_backend_certificate = network_stack.backend_certificate
props.network_frontend_certificate = network_stack.frontend_certificate

data_stack = DataStack(app, f"{settings.PROJECT_NAME}-data-stack", props, env=env)
props.data_aurora_db = data_stack.aurora_db
props.data_s3_public_images = data_stack.s3_public_images
props.data_s3_private_images = data_stack.s3_private_images
props.data_cloudfront_public_images = data_stack.cloudfront_public_images
props.data_cloudfront_private_images = data_stack.cloudfront_private_images

compute_stack = ComputeStack(
    app, f"{settings.PROJECT_NAME}-compute-stack", props, env=env
)

data_stack.add_dependency(network_stack)
compute_stack.add_dependency(data_stack)

app.synth()
