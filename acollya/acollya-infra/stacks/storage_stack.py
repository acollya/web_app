"""
Storage Stack - S3 buckets and CloudFront CDN.

Buckets:
  - acollya-media-{stage}:  Program PDFs, videos, user assets - served via CloudFront
  - acollya-backups-{stage}: Database backups - private, lifecycle to Glacier after 30d
  - acollya-lambda-{stage}:  Lambda deployment packages (used by CI/CD)

CloudFront:
  - Origin: media bucket (S3)
  - Signed URLs via OAC (Origin Access Control) - no public bucket access
  - Cache behaviors: PDFs (1 day), videos (7 days), images (30 days)
  - Price class PriceClass.PRICE_CLASS_100 - North America + Europe only
    (switch to ALL for Brazil users; sa-east-1 edge locations in PriceClass_ALL)
"""
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
    CfnOutput,
)
from constructs import Construct


class StorageStack(Stack):
    def __init__(self, scope: Construct, id: str, stage: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.stage = stage
        is_prod = stage == "prod"

        # ── Media Bucket ──────────────────────────────────────────────────────
        self.media_bucket = s3.Bucket(
            self, "MediaBucket",
            bucket_name=f"acollya-media-{stage}-{self.account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=is_prod,
            removal_policy=RemovalPolicy.RETAIN if is_prod else RemovalPolicy.DESTROY,
            auto_delete_objects=not is_prod,
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.HEAD],
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                    max_age=3000,
                )
            ],
            lifecycle_rules=[
                # Clean up incomplete multipart uploads
                s3.LifecycleRule(
                    abort_incomplete_multipart_upload_after=Duration.days(7),
                )
            ],
        )

        # ── Backups Bucket ────────────────────────────────────────────────────
        self.backups_bucket = s3.Bucket(
            self, "BackupsBucket",
            bucket_name=f"acollya-backups-{stage}-{self.account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=False,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(30),
                        )
                    ],
                    expiration=Duration.days(365),
                )
            ],
        )

        # ── Lambda Code Bucket ────────────────────────────────────────────────
        self.lambda_bucket = s3.Bucket(
            self, "LambdaBucket",
            bucket_name=f"acollya-lambda-{stage}-{self.account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,  # Keep versions for Lambda rollback
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                # Keep only last 5 versions per object
                s3.LifecycleRule(
                    noncurrent_version_expiration=Duration.days(30),
                    noncurrent_versions_to_retain=5,
                )
            ],
        )

        # ── CloudFront Distribution ───────────────────────────────────────────
        # OAC - Origin Access Control (modern replacement for OAI)
        oac = cloudfront.S3OriginAccessControl(
            self, "MediaOac",
            signing=cloudfront.Signing.SIGV4_NO_OVERRIDE,
        )

        self.distribution = cloudfront.Distribution(
            self, "MediaCdn",
            comment=f"Acollya media CDN - {stage}",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(
                    self.media_bucket,
                    origin_access_control=oac,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                compress=True,
            ),
            additional_behaviors={
                # PDFs - 1 day cache
                "/programs/*/chapters/*.pdf": cloudfront.BehaviorOptions(
                    origin=origins.S3BucketOrigin.with_origin_access_control(
                        self.media_bucket,
                        origin_access_control=oac,
                    ),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy(
                        self, "PdfCachePolicy",
                        cache_policy_name=f"acollya-pdf-cache-{stage}",
                        default_ttl=Duration.days(1),
                        max_ttl=Duration.days(7),
                        min_ttl=Duration.seconds(0),
                    ),
                    trusted_key_groups=None,  # Will add signed URLs in Phase 3
                ),
            },
            # Use PriceClass_ALL to include Brazilian edge locations (GRU)
            price_class=cloudfront.PriceClass.PRICE_CLASS_ALL,
            minimum_protocol_version=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
            http_version=cloudfront.HttpVersion.HTTP2_AND_3,
            enable_logging=is_prod,
        )

        # Grant CloudFront OAC read access to media bucket
        self.media_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowCloudFrontOAC",
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("cloudfront.amazonaws.com")],
                actions=["s3:GetObject"],
                resources=[self.media_bucket.arn_for_objects("*")],
                conditions={
                    "StringEquals": {
                        "AWS:SourceArn": f"arn:aws:cloudfront::{self.account}:distribution/{self.distribution.distribution_id}"
                    }
                },
            )
        )

        # ── Outputs ───────────────────────────────────────────────────────────
        CfnOutput(self, "MediaBucketName", value=self.media_bucket.bucket_name, export_name=f"AcollyaMediaBucket-{stage}")
        CfnOutput(self, "CdnDomain", value=self.distribution.distribution_domain_name, export_name=f"AcollyaCdnDomain-{stage}")
        CfnOutput(self, "CdnDistributionId", value=self.distribution.distribution_id, export_name=f"AcollyaCdnId-{stage}")
