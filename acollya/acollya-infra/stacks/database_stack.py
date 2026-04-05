"""
Database Stack - RDS PostgreSQL with pgvector extension.

Instance sizing:
  Phase 0 (dev/launch): db.t3.micro - $13/month, 1 vCPU, 1GB RAM
  Phase 3 (10k users):  db.t3.small - $26/month
  Phase 6 (100k users): Migrate to Aurora Serverless v2

pgvector note:
  The extension is available on PostgreSQL 15+ with RDS.
  Run setup_database.py after first deploy to enable it:
    python scripts/setup_database.py --stage dev
"""
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
    CfnOutput,
)
from constructs import Construct


class DatabaseStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc: ec2.Vpc,
        lambda_sg: ec2.SecurityGroup,
        stage: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self.stage = stage
        is_prod = stage == "prod"

        # ── PostgreSQL engine version (using .of() for CDK version independence)
        pg_version = rds.PostgresEngineVersion.of("15.10", "15")

        # ── Parameter Group - enables pgvector ───────────────────────────────
        param_group = rds.ParameterGroup(
            self, "DbParamGroup",
            engine=rds.DatabaseInstanceEngine.postgres(version=pg_version),
            description=f"Acollya PostgreSQL 15 params - {stage}",
            parameters={
                "shared_preload_libraries": "pg_stat_statements",
                "pg_stat_statements.track": "ALL",
                "log_min_duration_statement": "1000" if is_prod else "500",
                "log_connections": "1",
                "log_disconnections": "1",
            },
        )

        # ── Subnet Group - private subnets ────────────────────────────────────
        subnet_group = rds.SubnetGroup(
            self, "DbSubnetGroup",
            vpc=vpc,
            description=f"Acollya RDS subnet group - {stage}",
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
        )

        # ── RDS Instance ──────────────────────────────────────────────────────
        self.db_instance = rds.DatabaseInstance(
            self, "AcollyaDb",
            instance_identifier=f"acollya-db-{stage}",
            engine=rds.DatabaseInstanceEngine.postgres(version=pg_version),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3,
                ec2.InstanceSize.MICRO if not is_prod else ec2.InstanceSize.SMALL,
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[self._create_db_sg(vpc, lambda_sg)],
            subnet_group=subnet_group,
            parameter_group=param_group,
            database_name="acollya",
            credentials=rds.Credentials.from_generated_secret(
                "acollya_admin",
                secret_name=f"acollya/{stage}/db-credentials",
            ),
            # Storage
            allocated_storage=20,
            max_allocated_storage=100,  # Auto-scaling up to 100GB
            storage_type=rds.StorageType.GP3,
            storage_encrypted=True,
            # Availability - Single AZ dev, Multi-AZ prod
            multi_az=is_prod,
            # Backups — 0 days disables automated backups (required for Free Tier dev)
            backup_retention=Duration.days(0 if not is_prod else 7),
            delete_automated_backups=not is_prod,
            preferred_backup_window="03:00-04:00",  # UTC = 00:00-01:00 BRT
            preferred_maintenance_window="Mon:04:00-Mon:05:00",
            # Monitoring
            enable_performance_insights=True,
            performance_insight_retention=rds.PerformanceInsightRetention.DEFAULT,  # 7 days free
            monitoring_interval=Duration.seconds(60),
            cloudwatch_logs_exports=["postgresql"],
            # Protection
            deletion_protection=is_prod,
            removal_policy=RemovalPolicy.SNAPSHOT if is_prod else RemovalPolicy.DESTROY,
            publicly_accessible=False,
        )

        # ── Expose outputs ────────────────────────────────────────────────────
        self.db_secret = self.db_instance.secret
        self.db_host = self.db_instance.db_instance_endpoint_address

        # ── Outputs ───────────────────────────────────────────────────────────
        CfnOutput(
            self, "DbEndpoint",
            value=self.db_instance.db_instance_endpoint_address,
            export_name=f"AcollyaDbEndpoint-{stage}",
        )
        CfnOutput(
            self, "DbSecretArn",
            value=self.db_instance.secret.secret_arn,
            export_name=f"AcollyaDbSecretArn-{stage}",
        )

    def _create_db_sg(
        self,
        vpc: ec2.Vpc,
        lambda_sg: ec2.SecurityGroup,
    ) -> ec2.SecurityGroup:
        """RDS security group - only allows PostgreSQL from Lambda SG."""
        sg = ec2.SecurityGroup(
            self, "DbInstanceSg",
            vpc=vpc,
            security_group_name=f"acollya-rds-sg-{self.stage}",
            description="Acollya RDS PostgreSQL instance",
            allow_all_outbound=False,
        )
        sg.add_ingress_rule(
            peer=lambda_sg,
            connection=ec2.Port.tcp(5432),
            description="PostgreSQL from Lambda",
        )
        return sg
