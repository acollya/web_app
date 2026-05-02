"""
API Stack - Lambda functions + API Gateway HTTP API.

Architecture:
  - api_lambda:  Handles all CRUD endpoints (FastAPI/Mangum, monolithic)
  - chat_lambda: Handles /api/v1/chat/stream (SSE/streaming, separate function
                 with provisioned concurrency to eliminate cold starts)

API Gateway:
  - HTTP API (cheaper than REST API: $1/M requests vs $3.50/M)
  - JWT authorizer (validates Bearer tokens before hitting Lambda)
  - Routes:
      ANY /api/{proxy+}  → api_lambda
      POST /api/v1/chat/stream → chat_lambda (streaming)

Note on Lambda Streaming:
  AWS Lambda Response Streaming requires Lambda Function URLs or
  API Gateway with integration type AWS_PROXY + invoke mode RESPONSE_STREAM.
  The chat Lambda uses a Function URL directly for streaming, bypassing
  API Gateway's 29-second timeout limitation.
"""
from pathlib import Path
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    aws_ec2 as ec2,
    aws_lambda as _lambda,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations,
    aws_secretsmanager as secretsmanager,
    aws_s3 as s3,
    aws_iam as iam,
    aws_logs as logs,
    CfnOutput,
    BundlingOptions,
)
from constructs import Construct

# Path to backend code (relative to infra directory)
BACKEND_PATH = str(Path(__file__).parent.parent.parent / "acollya-backend")


class ApiStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc: ec2.Vpc,
        lambda_sg: ec2.SecurityGroup,
        db_secret: secretsmanager.ISecret,
        db_host: str,
        redis_host: str,
        redis_port: str,
        redis_tls: bool,
        media_bucket: s3.Bucket,
        stage: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self.stage = stage
        is_prod = stage == "prod"

        # Mobile-only app — native clients don't send CORS preflight.
        # Dev keeps localhost origins for tooling (Swagger UI, curl).
        if stage in ("prod", "staging"):
            cors_origins: list[str] = []
        else:
            cors_origins = ["http://localhost:8000", "http://localhost:19006", "http://127.0.0.1:8000"]

        # ── Shared environment variables ──────────────────────────────────────
        shared_env = {
            "STAGE": stage,
            "AWS_ACCOUNT_ID": self.account,
            "DB_HOST": db_host,
            "DB_PORT": "5432",
            "DB_NAME": "acollya",
            "DB_SECRET_ARN": db_secret.secret_arn,
            "REDIS_HOST": redis_host,
            "REDIS_PORT": redis_port,
            "REDIS_TLS": "true" if redis_tls else "false",
            "MEDIA_BUCKET": media_bucket.bucket_name,
            "JWT_SECRET_ARN": f"acollya/{stage}/jwt",
            "OPENAI_SECRET_ARN": f"acollya/{stage}/openai",
            "ANTHROPIC_SECRET_ARN": f"acollya/{stage}/anthropic",
            "LOG_LEVEL": "INFO" if is_prod else "DEBUG",
            "POWERTOOLS_SERVICE_NAME": "acollya-api",
            "POWERTOOLS_METRICS_NAMESPACE": "Acollya",
        }

        # ── IAM Role (shared between both Lambdas) ────────────────────────────
        lambda_role = self._create_lambda_role(db_secret, media_bucket)

        # ── CRUD API Lambda ───────────────────────────────────────────────────
        self.api_lambda = _lambda.Function(
            self, "ApiFunction",
            function_name=f"acollya-api-{stage}",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset(
                BACKEND_PATH,
                bundling=BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output --quiet && "
                        "cp -r app handler.py /asset-output",
                    ],
                ),
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[lambda_sg],
            environment=shared_env,
            memory_size=512,
            timeout=Duration.seconds(30),
            tracing=_lambda.Tracing.ACTIVE,
            role=lambda_role,
        )

        # ── Chat Streaming Lambda ─────────────────────────────────────────────
        # Separate function with larger memory (streaming AI responses)
        self.chat_lambda = _lambda.Function(
            self, "ChatFunction",
            function_name=f"acollya-chat-{stage}",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.chat_handler",
            code=_lambda.Code.from_asset(
                BACKEND_PATH,
                bundling=BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output --quiet && "
                        "cp -r app handler.py /asset-output",
                    ],
                ),
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[lambda_sg],
            environment={**shared_env, "POWERTOOLS_SERVICE_NAME": "acollya-chat"},
            memory_size=1024,
            timeout=Duration.minutes(5),  # Allow long-running SSE streams
            tracing=_lambda.Tracing.ACTIVE,
            role=lambda_role,
        )

        # Provisioned concurrency on chat Lambda - eliminates cold starts.
        # Only enable in prod (costs ~$0.015/GB-hr). The Function URL must be
        # attached to the alias (not the function), otherwise traffic hits
        # $LATEST and the provisioned containers stay idle.
        if is_prod:
            version = self.chat_lambda.current_version
            alias = _lambda.Alias(
                self, "ChatProdAlias",
                alias_name="live",
                version=version,
                provisioned_concurrent_executions=2,
            )
            url_target = alias
        else:
            url_target = self.chat_lambda

        # ── Lambda Function URL for Chat Streaming ────────────────────────────
        # Direct Function URL bypasses API Gateway 29s timeout for SSE.
        # auth_type=NONE — JWT validation is enforced inside the function.
        # CORS is locked to stage-specific origins for browser-client protection;
        # native mobile clients don't use CORS so an empty allowed_origins list
        # simply results in no CORS headers being emitted (correct for mobile).
        self.chat_url = url_target.add_function_url(
            auth_type=_lambda.FunctionUrlAuthType.NONE,
            cors=_lambda.FunctionUrlCorsOptions(
                allowed_origins=cors_origins,
                allowed_methods=[_lambda.HttpMethod.POST],
                allowed_headers=["Content-Type", "Authorization"],
                max_age=Duration.seconds(86400),
            ),
            invoke_mode=_lambda.InvokeMode.RESPONSE_STREAM,
        )

        # ── API Gateway HTTP API ──────────────────────────────────────────────
        # Only attach CORS preflight when there are origins to allow.
        # Passing allow_origins=[] would instruct API Gateway to respond to
        # OPTIONS with no valid origin, breaking browser clients. For mobile-
        # only stages (prod/staging), simply omit cors_preflight entirely.
        http_api_kwargs: dict = {
            "api_name": f"acollya-api-{stage}",
            "description": f"Acollya REST API - {stage}",
        }
        if cors_origins:
            http_api_kwargs["cors_preflight"] = apigwv2.CorsPreflightOptions(
                allow_origins=cors_origins,
                allow_methods=[
                    apigwv2.CorsHttpMethod.GET,
                    apigwv2.CorsHttpMethod.POST,
                    apigwv2.CorsHttpMethod.PUT,
                    apigwv2.CorsHttpMethod.PATCH,
                    apigwv2.CorsHttpMethod.DELETE,
                    apigwv2.CorsHttpMethod.OPTIONS,
                ],
                allow_headers=["Content-Type", "Authorization", "X-Request-Id"],
                max_age=Duration.seconds(86400),
            )
        http_api = apigwv2.HttpApi(self, "AcollyaHttpApi", **http_api_kwargs)

        # Lambda integration (all routes → api_lambda)
        api_integration = integrations.HttpLambdaIntegration(
            "ApiIntegration", self.api_lambda,
            payload_format_version=apigwv2.PayloadFormatVersion.VERSION_2_0,
        )

        # Route: ALL /api/{proxy+} → api_lambda
        http_api.add_routes(
            path="/api/{proxy+}",
            methods=[apigwv2.HttpMethod.ANY],
            integration=api_integration,
        )

        # Route: health check (no auth)
        http_api.add_routes(
            path="/health",
            methods=[apigwv2.HttpMethod.GET],
            integration=api_integration,
        )

        # ── Log group for API Gateway ─────────────────────────────────────────
        apigw_log_group = logs.LogGroup(
            self, "ApiGwLogGroup",
            log_group_name=f"/aws/apigateway/acollya-{stage}",
            # 1 year for prod (audit trail), 1 month for dev (cost)
            retention=logs.RetentionDays.ONE_YEAR if is_prod else logs.RetentionDays.ONE_MONTH,
        )

        # Enable access logging + throttling on default stage via CfnStage
        stage_resource = http_api.default_stage.node.default_child
        stage_resource.access_log_settings = {
            "destinationArn": apigw_log_group.log_group_arn,
            "format": '{"requestId":"$context.requestId","ip":"$context.identity.sourceIp","requestTime":"$context.requestTime","httpMethod":"$context.httpMethod","routeKey":"$context.routeKey","status":"$context.status","responseLength":"$context.responseLength","integrationError":"$context.integrationErrorMessage"}',
        }
        stage_resource.default_route_settings = {
            "throttlingBurstLimit": 100,
            "throttlingRateLimit": 50,
        }

        # ── Expose outputs ────────────────────────────────────────────────────
        self.http_api_id = http_api.api_id
        self.api_endpoint = http_api.api_endpoint

        # ── Outputs ───────────────────────────────────────────────────────────
        CfnOutput(self, "ApiEndpoint", value=http_api.api_endpoint, export_name=f"AcollyaApiEndpoint-{stage}")
        CfnOutput(self, "ChatFunctionUrl", value=self.chat_url.url, export_name=f"AcollyaChatUrl-{stage}")
        CfnOutput(self, "ApiLambdaArn", value=self.api_lambda.function_arn, export_name=f"AcollyaApiLambdaArn-{stage}")

    def _create_lambda_role(
        self,
        db_secret: secretsmanager.ISecret,
        media_bucket: s3.Bucket,
    ) -> iam.Role:
        """IAM role with least-privilege permissions for Lambda functions."""
        role = iam.Role(
            self, "LambdaRole",
            role_name=f"acollya-lambda-role-{self.stage}",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaVPCAccessExecutionRole"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSXRayDaemonWriteAccess"
                ),
            ],
            inline_policies={
                "SecretsManagerRead": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["secretsmanager:GetSecretValue"],
                            resources=[
                                db_secret.secret_arn,
                                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:acollya/{self.stage}/*",
                            ],
                        )
                    ]
                ),
                "S3MediaAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
                            resources=[f"{media_bucket.bucket_arn}/*"],
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["s3:ListBucket"],
                            resources=[media_bucket.bucket_arn],
                        ),
                    ]
                ),
                "CloudWatchMetrics": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["cloudwatch:PutMetricData"],
                            resources=["*"],
                            conditions={
                                "StringEquals": {"cloudwatch:namespace": "Acollya"}
                            },
                        )
                    ]
                ),
            },
        )
        return role
