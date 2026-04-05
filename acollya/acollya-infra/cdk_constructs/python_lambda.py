"""
Reusable Python Lambda construct with X-Ray, structured logging, and VPC support.

Usage:
  from cdk_constructs.python_lambda import PythonLambdaFunction

  fn = PythonLambdaFunction(
      self, "MyFunction",
      function_name="acollya-api-dev",
      code_path=str(Path(__file__).parent.parent.parent / "acollya-backend"),
      handler="handler.handler",
      vpc=vpc,
      lambda_sg=lambda_sg,
      environment={"STAGE": "dev"},
  )
"""
from pathlib import Path
from aws_cdk import (
    Duration,
    aws_ec2 as ec2,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_logs as logs,
    BundlingOptions,
)
from constructs import Construct


class PythonLambdaFunction(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        function_name: str,
        code_path: str,
        handler: str,
        vpc: ec2.Vpc,
        lambda_sg: ec2.SecurityGroup,
        environment: dict,
        memory_size: int = 512,
        timeout_seconds: int = 30,
        streaming: bool = False,
        log_retention_days: int = 30,
    ) -> None:
        super().__init__(scope, id)

        # ── IAM Role ──────────────────────────────────────────────────────────
        role = iam.Role(
            self, "Role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaVPCAccessExecutionRole"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSXRayDaemonWriteAccess"
                ),
            ],
        )

        # ── Log Group (explicit, with retention) ──────────────────────────────
        log_group = logs.LogGroup(
            self, "LogGroup",
            log_group_name=f"/aws/lambda/{function_name}",
            retention=logs.RetentionDays.ONE_MONTH
            if log_retention_days == 30
            else logs.RetentionDays.THREE_MONTHS,
        )
        log_group.grant_write(role)

        # ── Lambda Function ───────────────────────────────────────────────────
        self.function = _lambda.Function(
            self, "Function",
            function_name=function_name,
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler=handler,
            code=_lambda.Code.from_asset(
                code_path,
                bundling=BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                    command=[
                        "bash", "-c",
                        (
                            "pip install -r requirements.txt -t /asset-output --quiet && "
                            "cp -r app handler.py /asset-output"
                        ),
                    ],
                ),
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[lambda_sg],
            environment=environment,
            memory_size=memory_size,
            timeout=Duration.seconds(timeout_seconds),
            tracing=_lambda.Tracing.ACTIVE,  # X-Ray
            role=role,
            # Streaming mode for chat Lambda
            **({"invoke_mode": _lambda.InvokeMode.RESPONSE_STREAM} if streaming else {}),
        )

    @property
    def function_arn(self) -> str:
        return self.function.function_arn

    @property
    def function_name(self) -> str:
        return self.function.function_name

    def grant_secret_read(self, secret) -> None:
        """Allow this Lambda to read a Secrets Manager secret."""
        secret.grant_read(self.function)

    def grant_s3_read_write(self, bucket) -> None:
        """Allow this Lambda to read/write an S3 bucket."""
        bucket.grant_read_write(self.function)
