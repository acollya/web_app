"""
Database Stack - RDS PostgreSQL with pgvector extension + RDS Proxy.

Instance sizing:
  Phase 0 (dev/launch): db.t3.micro - $13/month, 1 vCPU, 1GB RAM
  Phase 3 (10k users):  db.t3.small - $26/month
  Phase 6 (100k users): Migrate to Aurora Serverless v2

RDS Proxy:
  Sits between Lambda and RDS to multiplex connections and prevent exhaustion.
  Lambda's NullPool means every cold start opens a new TCP connection to RDS.
  Without a proxy, bursts of cold starts (deploys, traffic spikes) can hit
  PostgreSQL's max_connections limit and cause 503s.

  Cost: ~$0.015/proxy-vCPU/hour ≈ $11/month for db.t3.micro.
  Lambda always connects via proxy endpoint (self.proxy_endpoint).

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
                "log_min_duration_statement": "200" if is_prod else "500",
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

        # ── Security Groups ───────────────────────────────────────────────────
        # Create both SGs before adding cross-referencing rules.
        db_sg, proxy_sg = self._create_security_groups(vpc, lambda_sg)

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
            security_groups=[db_sg],
            subnet_group=subnet_group,
            parameter_group=param_group,
            database_name="acollya",
            credentials=rds.Credentials.from_generated_secret(
                "acollya_admin",
                secret_name=f"acollya/{stage}/db-credentials",
            ),
            # Storage
            allocated_storage=20,
            max_allocated_storage=100,
            storage_type=rds.StorageType.GP3,
            storage_encrypted=True,
            # Availability
            multi_az=is_prod,
            # Minimum 1 day in dev (0 disables backups entirely — no recovery possible)
            backup_retention=Duration.days(1 if not is_prod else 7),
            delete_automated_backups=False,
            preferred_backup_window="03:00-04:00",
            preferred_maintenance_window="Mon:04:00-Mon:05:00",
            # Monitoring
            enable_performance_insights=True,
            performance_insight_retention=rds.PerformanceInsightRetention.DEFAULT,
            monitoring_interval=Duration.seconds(60),
            cloudwatch_logs_exports=["postgresql"],
            # Protection
            deletion_protection=is_prod,
            removal_policy=RemovalPolicy.SNAPSHOT if is_prod else RemovalPolicy.DESTROY,
            publicly_accessible=False,
        )

        # ── RDS Proxy ─────────────────────────────────────────────────────────
        # Multiplexes Lambda connections into a persistent pool towards RDS.
        # Lambda always connects to self.proxy_endpoint (never direct to RDS).
        self.db_proxy = rds.DatabaseProxy(
            self, "AcollyaDbProxy",
            proxy_target=rds.ProxyTarget.from_instance(self.db_instance),
            secrets=[self.db_instance.secret],  # type: ignore[list-item]
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[proxy_sg],
            db_proxy_name=f"acollya-db-proxy-{stage}",
            idle_client_timeout=Duration.minutes(30),
            # Leave 10% headroom for emergency admin connections
            max_connections_percent=90,
            require_tls=True,
            iam_auth=False,  # Secrets Manager credentials — no app code changes needed
        )

        # ── Expose outputs ────────────────────────────────────────────────────
        self.db_secret = self.db_instance.secret
        # Lambda must connect via proxy endpoint to benefit from connection pooling
        self.proxy_endpoint = self.db_proxy.endpoint
        # db_host kept for backward compatibility; points to proxy, not instance
        self.db_host = self.db_proxy.endpoint

        # ── Outputs ───────────────────────────────────────────────────────────
        CfnOutput(
            self, "DbInstanceEndpoint",
            value=self.db_instance.db_instance_endpoint_address,
            export_name=f"AcollyaDbInstanceEndpoint-{stage}",
        )
        CfnOutput(
            self, "DbProxyEndpoint",
            value=self.db_proxy.endpoint,
            export_name=f"AcollyaDbProxyEndpoint-{stage}",
        )
        CfnOutput(
            self, "DbSecretArn",
            value=self.db_instance.secret.secret_arn,  # type: ignore[union-attr]
            export_name=f"AcollyaDbSecretArn-{stage}",
        )

    def _create_security_groups(
        self,
        vpc: ec2.Vpc,
        lambda_sg: ec2.SecurityGroup,
    ) -> tuple[ec2.SecurityGroup, ec2.SecurityGroup]:
        """
        Create and wire the RDS instance SG and the RDS Proxy SG.

        Traffic flow: Lambda → Proxy → RDS
          lambda_sg  →  proxy_sg  : inbound 5432
          proxy_sg   →  db_sg     : inbound 5432 + outbound 5432
        """
        db_sg = ec2.SecurityGroup(
            self, "DbInstanceSg",
            vpc=vpc,
            security_group_name=f"acollya-rds-sg-{self.stage}",
            description="Acollya RDS PostgreSQL instance",
            allow_all_outbound=False,
        )

        proxy_sg = ec2.SecurityGroup(
            self, "DbProxySg",
            vpc=vpc,
            security_group_name=f"acollya-rds-proxy-sg-{self.stage}",
            description="Acollya RDS Proxy",
            allow_all_outbound=False,
        )

        # Lambda → Proxy (inbound on proxy)
        proxy_sg.add_ingress_rule(
            peer=lambda_sg,
            connection=ec2.Port.tcp(5432),
            description="PostgreSQL from Lambda",
        )
        # Proxy → RDS (outbound from proxy, inbound on RDS)
        proxy_sg.add_egress_rule(
            peer=db_sg,
            connection=ec2.Port.tcp(5432),
            description="PostgreSQL to RDS instance",
        )
        db_sg.add_ingress_rule(
            peer=proxy_sg,
            connection=ec2.Port.tcp(5432),
            description="PostgreSQL from RDS Proxy",
        )

        return db_sg, proxy_sg
