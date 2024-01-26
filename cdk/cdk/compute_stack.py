from aws_cdk import (
    Stack,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as cloudfront_origins,
    aws_ec2 as ec2,
    aws_ecr_assets as ecr_assets,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_elasticloadbalancingv2 as elbv2,
    aws_logs as logs,
    aws_route53 as r53,
    aws_route53_targets as r53_targets,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct

from cdk.util import settings, Props


class ComputeStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, props: Props, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # COMPLETED FOR YOU: ECS cluster for container hosting
        cluster = ecs.Cluster(
            self, f"{settings.PROJECT_NAME}-cluster", vpc=props.network_vpc
        )

        # COMPLETED FOR YOU: Secret for JWT signing key
        app_secret_key = secretsmanager.Secret(
            self,
            f"{settings.PROJECT_NAME}-app-secret-key",
            description="Yoctogram App JWT Signing Key",
        )

        # FILLMEIN: Fargate task definition
        fargate_task_definition = ecs.FargateTaskDefinition(
            self,
            f"{settings.PROJECT_NAME}-fargate-task-definition",
        )

        # FILLMEIN: Grant the task definition's task role access to the database and signing key secrets, as well as the S3 buckets

        # FILLMEIN: Add a container to the Fargate task definition
        fargate_task_definition.add_container(
            f"{settings.PROJECT_NAME}-app-container",
            container_name=f"{settings.PROJECT_NAME}-app-container",
        )

        # FILLMEIN: Finish the Fargate service backend deployment
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            f"{settings.PROJECT_NAME}-fargate-service",
        )

        # COMPLETED FOR YOU: Fargate service settings
        fargate_service.target_group.configure_health_check(path="/api/v1/health")

        fargate_service.service.connections.allow_to(
            props.data_aurora_db, ec2.Port.tcp(5432), "DB access"
        )

        # COMPLETED FOR YOU: S3 frontend deployment setup steps
        frontend_bucket = s3.Bucket(
            self,
            f"{settings.PROJECT_NAME}-frontend-deployment-bucket",
        )

        access_identity = cloudfront.OriginAccessIdentity(
            self,
            f"{settings.PROJECT_NAME}-frontend-access-identity",
        )
        frontend_bucket.grant_read(access_identity)

        frontend_deployment = s3_deployment.BucketDeployment(
            self,
            f"{settings.PROJECT_NAME}-frontend-deployment",
            sources=[s3_deployment.Source.asset(f"{settings.YOCTOGRAM_WEB_DIR}/dist")],
            destination_bucket=frontend_bucket,
        )

        # FILLMEIN: Cloudfront distribution for frontend
        frontend_distribution = cloudfront.Distribution(
            self,
            f"{settings.PROJECT_NAME}-frontend-distribution",
        )

        # COMPLETED FOR YOU: DNS A record for Cloudfront frontend
        frontend_domain = r53.ARecord(
            self,
            f"{settings.PROJECT_NAME}-frontend-domain",
            zone=props.network_hosted_zone,
            record_name=settings.APP_DOMAIN,
            target=r53.RecordTarget.from_alias(
                r53_targets.CloudFrontTarget(frontend_distribution)
            ),
        )
