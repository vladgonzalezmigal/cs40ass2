import string
from typing import Dict, Optional

from aws_cdk import (
    aws_certificatemanager as acm,
    aws_cloudfront as cloudfront,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_route53 as r53,
    aws_s3 as s3,
)
from pydantic import field_validator
from pydantic_core.core_schema import ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    PROJECT_NAME: str = "yoctogram"
    COURSE_DNS_ROOT: str = "infracourse.cloud"

    SUNET: str
    SUNET_DNS_ROOT: Optional[str] = None
    APP_DOMAIN: Optional[str] = None
    REGION: str = "us-west-2"
    YOCTOGRAM_APP_DIR: str = "../app"
    YOCTOGRAM_WEB_DIR: str = "../web"

    DB_SPECIAL_CHARS_EXCLUDE: str = (
        string.printable.replace(string.ascii_letters, "")
        .replace(string.digits, "")
        .replace(string.whitespace, " ")
        .replace("_", "")
    )

    DB_SECRET_MAPPING: Dict[str, str] = {
        "POSTGRES_HOST": "host",
        "POSTGRES_PORT": "port",
        "POSTGRES_USER": "username",
        "POSTGRES_PASSWORD": "password",
        "POSTGRES_DB": "dbname",
    }

    CDK_DEFAULT_ACCOUNT: str

    @field_validator("SUNET_DNS_ROOT", mode="before")
    @classmethod
    def assemble_sunet_dns_root(cls, v: Optional[str], info: ValidationInfo) -> str:
        if isinstance(v, str):
            return v
        return f"{info.data.get('SUNET')}.{info.data.get('COURSE_DNS_ROOT')}"

    @field_validator("APP_DOMAIN", mode="before")
    @classmethod
    def assemble_app_domain(cls, v: Optional[str], info: ValidationInfo) -> str:
        if isinstance(v, str):
            return v
        return f"{info.data.get('PROJECT_NAME')}.{info.data.get('SUNET_DNS_ROOT')}"


settings = Settings()


class Props:
    network_vpc: ec2.IVpc
    network_backend_certificate: acm.ICertificate
    network_frontend_certificate: acm.ICertificate
    network_hosted_zone: r53.IHostedZone
    data_aurora_db: rds.ServerlessCluster
    data_s3_public_images: s3.Bucket
    data_s3_private_images: s3.Bucket
    data_cloudfront_public_images: cloudfront.Distribution
    data_cloudfront_private_images: cloudfront.Distribution
