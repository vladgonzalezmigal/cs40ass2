from aws_cdk import (
    Stack,
    aws_certificatemanager as acm,
    aws_ec2 as ec2,
    aws_route53 as r53,
)
from constructs import Construct

from cdk.util import settings, Props


class NetworkStack(Stack):
    backend_certificate: acm.ICertificate
    frontend_certificate: acm.ICertificate
    vpc: ec2.IVpc

    def __init__(
        self, scope: Construct, construct_id: str, props: Props, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # FILLMEIN: VPC
        self.vpc = ec2.Vpc(
            self,
            f"{settings.PROJECT_NAME}-vpc",
        )

        # FILLMEIN: TLS certificate for backend
        self.backend_certificate = acm.Certificate(
            self,
            f"{settings.PROJECT_NAME}-backend-certificate",
        )

        # COMPLETED FOR YOU: TLS certificate for frontend
        self.frontend_certificate = acm.DnsValidatedCertificate(
            self,
            f"{settings.PROJECT_NAME}-frontend-certificate",
            domain_name=settings.APP_DOMAIN,
            subject_alternative_names=[f"*.{settings.APP_DOMAIN}"],
            hosted_zone=props.network_hosted_zone,
            region="us-east-1",  # Cloudfront certificate needs to be in us-east-1
        )
