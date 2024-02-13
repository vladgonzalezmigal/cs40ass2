from aws_cdk import (
    Stack,
    aws_cloudfront as cloudfront,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_s3 as s3,
)
from aws_solutions_constructs import aws_cloudfront_s3 as cfs3
from constructs import Construct

from cdk.util import settings, Props


class DataStack(Stack):
    aurora_db: rds.ServerlessCluster
    s3_public_images: s3.Bucket
    s3_private_images: s3.Bucket
    cloudfront_public_images: cloudfront.Distribution
    cloudfront_private_images: cloudfront.Distribution

    def __init__(
        self, scope: Construct, construct_id: str, props: Props, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # FILLMEIN: Aurora Serverless Database
        self.aurora_db = rds.ServerlessCluster(
            self,
            f"{settings.PROJECT_NAME}-aurora-serverless",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_13_10
            ),
            vpc=props.network_vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            default_database_name="yoctogram", # was default_*
            credentials=rds.Credentials.from_generated_secret(
                username="yoctogram",  # Default username
                exclude_characters=settings.DB_SPECIAL_CHARS_EXCLUDE
            ),
            # deletion_protection=False,  # Set to True in production
        )

        # COMPLETED FOR YOU: S3 Buckets and Cloudfront CDN for images
        cloudfront_response_policy = cloudfront.ResponseHeadersPolicyProps(
            cors_behavior=cloudfront.ResponseHeadersCorsBehavior(
                access_control_allow_credentials=False,
                access_control_allow_headers=["*"],
                access_control_allow_methods=["GET", "POST", "PUT", "DELETE"],
                access_control_allow_origins=[f"https://{settings.APP_DOMAIN}"],
                origin_override=False,
            )
        )

        cloudfront_s3_public = cfs3.CloudFrontToS3(
            self,
            f"{settings.PROJECT_NAME}-public-images-s3-cloudfront",
            response_headers_policy_props=cloudfront_response_policy,
        )

        cloudfront_s3_private = cfs3.CloudFrontToS3(
            self,
            f"{settings.PROJECT_NAME}-private-images-s3-cloudfront",
            response_headers_policy_props=cloudfront_response_policy,
        )

        self.s3_public_images = cloudfront_s3_public.s3_bucket
        self.s3_private_images = cloudfront_s3_private.s3_bucket

        self.s3_public_images.add_cors_rule(
            allowed_origins=[f"https://{settings.APP_DOMAIN}"],
            allowed_methods=[
                s3.HttpMethods.GET,
                s3.HttpMethods.HEAD,
                s3.HttpMethods.PUT,
                s3.HttpMethods.POST,
                s3.HttpMethods.DELETE,
            ],
        )

        self.s3_private_images.add_cors_rule(
            allowed_origins=[f"https://{settings.APP_DOMAIN}"],
            allowed_methods=[
                s3.HttpMethods.GET,
                s3.HttpMethods.HEAD,
                s3.HttpMethods.PUT,
                s3.HttpMethods.POST,
                s3.HttpMethods.DELETE,
            ],
        )

        self.cloudfront_public_images = (
            cloudfront_s3_public.cloud_front_web_distribution
        )
        self.cloudfront_private_images = (
            cloudfront_s3_private.cloud_front_web_distribution
        )
