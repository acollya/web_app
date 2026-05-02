"""
Jobs Stack — Scheduled background Lambdas (EventBridge cron).

Architecture:
  - weekly_report_lambda      → handler_jobs.weekly_report_handler
      Cron: cron(0 21 ? * FRI *)   (Friday 21:00 UTC = 18:00 BRT)
      Generates a brief weekly emotional-pattern summary for each active user.
      Persists to Redis when available, otherwise logs to CloudWatch.
      Memory: 512MB, Timeout: 5min.

  - dependency_check_lambda   → handler_jobs.dependency_check_handler
      Cron: cron(0 9 * * ? *)      (Daily 09:00 UTC = 06:00 BRT)
      Flags users with excessive chatbot usage in the last 3 days.
      Memory: 512MB, Timeout: 3min.

Both Lambdas:
  - Run inside the same VPC + Security Group as api_lambda so they can reach
    RDS and ElastiCache without going through the public internet.
  - Share an IAM role granting Secrets Manager read (DB / OpenAI / Anthropic)
    and CloudWatch metrics publish under the "Acollya" namespace.
  - Receive identical environment variables to ApiStack so app.config.settings
    resolves the same DB host, Redis endpoint and secret ARNs.

Why a separate stack?
  - Decouples cron lifecycle from the API: deploying or rolling back JobsStack
    doesn't touch the user-facing API Lambda.
  - Keeps EventBridge rules and IAM permissions scoped to the cron functions,
    so an over-permissive change here cannot widen the API's attack surface.
"""
from pathlib import Path
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    aws_ec2 as ec2,
    aws_lambda as _lambda,
    aws_secretsmanager as secretsmanager,
    aws_s3 as s3,
    aws_iam as iam,
    aws_events as events,
    aws_events_targets as targets,
    aws_logs as logs,
    CfnOutput,
    BundlingOptions,
)
from constructs import Construct

# Path to backend code (relative to infra directory) — same source tree as ApiStack.
BACKEND_PATH = str(Path(__file__).parent.parent.parent / "acollya-backend")


class JobsStack(Stack):
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

        # ── Shared environment (mirror of ApiStack.shared_env) ────────────────
        # Keeping these in sync with ApiStack is critical: the same code reads
        # them via app.config.settings. If you add a new env var in ApiStack
        # that the cron handlers also need, mirror it here.
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
            "POWERTOOLS_SERVICE_NAME": "acollya-jobs",
            "POWERTOOLS_METRICS_NAMESPACE": "Acollya",
        }

        # ── IAM Role (shared by both cron Lambdas) ────────────────────────────
        # Same permissions surface as the API Lambda role: VPC access, X-Ray,
        # Secrets Manager read scoped to acollya/<stage>/* + the DB secret,
        # and CloudWatch metrics scoped to the Acollya namespace.
        jobs_lambda_role = iam.Role(
            self, "JobsLambdaRole",
            role_name=f"acollya-jobs-role-{stage}",
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
                                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:acollya/{stage}/*",
                            ],
                        )
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

        # ── Bundling (same recipe as ApiStack so we get a single zipped artefact
        #    containing requirements + the app/ package + handler_jobs.py) ─────
        # We deliberately copy handler.py too so a single layer image can serve
        # all three handlers if we ever consolidate them. Cost is a few KBs.
        bundling = BundlingOptions(
            image=_lambda.Runtime.PYTHON_3_12.bundling_image,
            command=[
                "bash", "-c",
                "pip install -r requirements.txt -t /asset-output --quiet && "
                "cp -r app handler.py handler_jobs.py /asset-output",
            ],
        )

        # ── Weekly Pattern Report Lambda ──────────────────────────────────────
        self.weekly_report_lambda = _lambda.Function(
            self, "WeeklyReportFunction",
            function_name=f"acollya-weekly-report-{stage}",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler_jobs.weekly_report_handler",
            code=_lambda.Code.from_asset(BACKEND_PATH, bundling=bundling),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[lambda_sg],
            environment={**shared_env, "POWERTOOLS_SERVICE_NAME": "acollya-weekly-report"},
            memory_size=512,
            # 5 min covers a few thousand active users at ~100ms LLM call each.
            # Beyond that scale, switch to Step Functions fan-out.
            timeout=Duration.minutes(5),
            tracing=_lambda.Tracing.ACTIVE,
            role=jobs_lambda_role,
            log_retention=(
                logs.RetentionDays.ONE_YEAR if is_prod else logs.RetentionDays.ONE_MONTH
            ),
        )

        # ── Dependency Check Lambda ───────────────────────────────────────────
        self.dependency_check_lambda = _lambda.Function(
            self, "DependencyCheckFunction",
            function_name=f"acollya-dependency-check-{stage}",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler_jobs.dependency_check_handler",
            code=_lambda.Code.from_asset(BACKEND_PATH, bundling=bundling),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[lambda_sg],
            environment={**shared_env, "POWERTOOLS_SERVICE_NAME": "acollya-dependency-check"},
            memory_size=512,
            # No LLM calls — pure SQL aggregation. 3 minutes is generous.
            timeout=Duration.minutes(3),
            tracing=_lambda.Tracing.ACTIVE,
            role=jobs_lambda_role,
            log_retention=(
                logs.RetentionDays.ONE_YEAR if is_prod else logs.RetentionDays.ONE_MONTH
            ),
        )

        # ── EventBridge: Weekly Report (Friday 21:00 UTC) ─────────────────────
        # Cron format for EventBridge differs from standard cron: it requires
        # 6 fields and the day-of-week / day-of-month fields cannot both be '*'.
        weekly_rule = events.Rule(
            self, "WeeklyReportSchedule",
            rule_name=f"acollya-weekly-report-{stage}",
            description="Friday 21:00 UTC (18:00 BRT) — weekly emotional pattern reports",
            schedule=events.Schedule.expression("cron(0 21 ? * FRI *)"),
        )
        weekly_rule.add_target(targets.LambdaFunction(self.weekly_report_lambda))

        # ── EventBridge: Daily Dependency Check (09:00 UTC) ───────────────────
        daily_rule = events.Rule(
            self, "DependencyCheckSchedule",
            rule_name=f"acollya-dependency-check-{stage}",
            description="Daily 09:00 UTC (06:00 BRT) — emotional dependency scan",
            schedule=events.Schedule.expression("cron(0 9 * * ? *)"),
        )
        daily_rule.add_target(targets.LambdaFunction(self.dependency_check_lambda))

        # The events.Rule.add_target(targets.LambdaFunction(...)) helper
        # automatically creates the lambda:InvokeFunction permission for the
        # rule's principal, so we don't need to add it manually here.

        # ── Outputs ───────────────────────────────────────────────────────────
        CfnOutput(
            self, "WeeklyReportFunctionArn",
            value=self.weekly_report_lambda.function_arn,
            export_name=f"AcollyaWeeklyReportArn-{stage}",
        )
        CfnOutput(
            self, "DependencyCheckFunctionArn",
            value=self.dependency_check_lambda.function_arn,
            export_name=f"AcollyaDependencyCheckArn-{stage}",
        )
        CfnOutput(
            self, "WeeklyReportScheduleArn",
            value=weekly_rule.rule_arn,
            export_name=f"AcollyaWeeklyReportScheduleArn-{stage}",
        )
        CfnOutput(
            self, "DependencyCheckScheduleArn",
            value=daily_rule.rule_arn,
            export_name=f"AcollyaDependencyCheckScheduleArn-{stage}",
        )
