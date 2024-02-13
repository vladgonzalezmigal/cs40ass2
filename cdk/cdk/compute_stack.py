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
            cpu=512,
            memory_limit_mib=2048,
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.ARM64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX
            )
        )

        # FILLMEIN: Grant the task definition's task role access to the database and signing key secrets, as well as the S3 buckets
        # Granting access to secrets and S3 buckets
        app_secret_key.grant_read(fargate_task_definition.task_role)
        props.data_aurora_db.secret.grant_read(fargate_task_definition.task_role)
        props.data_s3_public_images.grant_read_write(fargate_task_definition.task_role)
        props.data_s3_private_images.grant_read_write(fargate_task_definition.task_role)
        
        # Assuming you have pushed your container image to ECR and have the URL
        container_image = ecs.ContainerImage.from_asset(
            directory=f"{settings.YOCTOGRAM_APP_DIR}"
        )

        # FILLMEIN: Add a container to the Fargate task definition
        container = fargate_task_definition.add_container(
            f"{settings.PROJECT_NAME}-app-container",
            container_name=f"{settings.PROJECT_NAME}-app-container",
            image=container_image,
            logging=ecs.AwsLogDriver(
                stream_prefix=f"{settings.PROJECT_NAME}-fargate",
                log_retention=logs.RetentionDays.ONE_WEEK,
            )
        )

        env_vars = {
            "PRODUCTION": "true",
            "DEBUG": "false",
            "FORWARD_FACING_NAME": f"yoctogram.{settings.SUNET}.infracourse.cloud",
            "PUBLIC_IMAGES_BUCKET": props.data_s3_public_images.bucket_name,
            "PRIVATE_IMAGES_BUCKET": props.data_s3_private_images.bucket_name,
            "PUBLIC_IMAGES_CLOUDFRONT_DISTRIBUTION": props.data_cloudfront_public_images.distribution_domain_name,
            "PRIVATE_IMAGES_CLOUDFRONT_DISTRIBUTION": props.data_cloudfront_private_images.distribution_domain_name,
        }

        for key, value in settings.DB_SECRET_MAPPING.items():
            secret = ecs.Secret.from_secrets_manager(props.data_aurora_db.secret, field=value)
            env_vars[key] = secret
        env_vars["SECRET_KEY"] = ecs.Secret.from_secrets_manager(app_secret_key)

         # Correctly add environment variables to the container
       
        for key, value in env_vars.items():
            if isinstance(value, ecs.Secret):
                container.add_secret(key, value)
            else:
                container.add_environment(key, value)

        

        # Adding health check to the container definition
        container.health_check = ecs.HealthCheck(
            command=["CMD-SHELL", "curl -f http://localhost/api/v1/health/ || exit 1"],
            # interval=aws_cdk.Duration.seconds(30),
            # timeout=aws_cdk.Duration.seconds(5),
            # retries=3,
        )

        container.add_port_mappings(ecs.PortMapping(container_port=80))
        # FILLMEIN: Finish the Fargate service backend deployment
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            f"{settings.PROJECT_NAME}-fargate-service",
            cluster=cluster,  # ECS cluster defined earlier
            task_definition=fargate_task_definition,  # The Fargate task definition we've configured
            public_load_balancer=True,  # Set to true if the service should be publicly accessible
            listener_port=443,  # Default listener port for HTTPS
            domain_name=f"api.yoctogram.{settings.SUNET}.infracourse.cloud",  # Domain name for the service
            domain_zone=props.network_hosted_zone,  # Hosted zone for the domain
            certificate=props.network_backend_certificate,  # TLS certificate for HTTPS
            redirect_http=True,  # Redirect HTTP to HTTPS
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
            default_behavior=cloudfront.BehaviorOptions(
                origin=cloudfront_origins.S3Origin(
                    frontend_bucket,
                    origin_access_identity=access_identity,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            default_root_object="index.html",  
            additional_behaviors={
                "/api/*": cloudfront.BehaviorOptions(
                    origin=cloudfront_origins.HttpOrigin(
                        f"api.yoctogram.{settings.SUNET}.infracourse.cloud",
                        http_port=80,
                        https_port=443,
                    ),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
                )
            },
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_page_path="/index.html",
                    response_http_status=200,
                )
            ],
            domain_names=[f"yoctogram.{settings.SUNET}.infracourse.cloud"],
            certificate=props.network_frontend_certificate,
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
