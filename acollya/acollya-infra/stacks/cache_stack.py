"""
Cache Stack — ElastiCache Redis for rate limiting and session management.

Uses:
  - Sliding window rate limiting (chat messages per day per user)
  - JWT refresh token storage with TTL-based revocation
  - API response caching for therapist lists / program metadata

Instance sizing:
  Phase 0 (dev/launch): cache.t3.micro — $13/month, 0.5GB RAM
  Phase 3 (10k users):  cache.t3.small — $26/month
  Phase 6 (100k users): cache.r6g.large with cluster mode

Note: ElastiCache Serverless (~$90/month minimum) is cheaper only at >100k users.
For Phase 0-2, standalone t3.micro is optimal.
"""
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_elasticache as elasticache,
    CfnOutput,
)
from constructs import Construct


class CacheStack(Stack):
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

        # ── Security Group ────────────────────────────────────────────────────
        # No fixed name — let CDK generate it to avoid conflicts on re-deploy
        redis_sg = ec2.SecurityGroup(
            self, "RedisSg",
            vpc=vpc,
            description="Acollya ElastiCache Redis",
            allow_all_outbound=False,
        )
        redis_sg.add_ingress_rule(
            peer=lambda_sg,
            connection=ec2.Port.tcp(6379),
            description="Redis from Lambda",
        )

        # ── Subnet Group ──────────────────────────────────────────────────────
        private_subnet_ids = [
            subnet.subnet_id
            for subnet in vpc.select_subnets(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ).subnets
        ]

        subnet_group = elasticache.CfnSubnetGroup(
            self, "RedisSubnetGroup",
            cache_subnet_group_name=f"acollya-redis-subnet-{stage}",
            description=f"Acollya Redis subnet group - {stage}",
            subnet_ids=private_subnet_ids,
        )

        # ── Redis Cluster ─────────────────────────────────────────────────────
        redis_cluster = elasticache.CfnCacheCluster(
            self, "AcollyaRedis",
            cluster_name=f"acollya-redis-{stage}",
            cache_node_type="cache.t3.micro" if not is_prod else "cache.t3.small",
            engine="redis",
            engine_version="7.1",
            num_cache_nodes=1,
            cache_subnet_group_name=subnet_group.cache_subnet_group_name,
            vpc_security_group_ids=[redis_sg.security_group_id],
            # Persistence — RDB snapshot every 12h for durability
            snapshot_retention_limit=1 if not is_prod else 3,
            snapshot_window="02:00-03:00",  # UTC = 23:00-00:00 BRT
            preferred_maintenance_window="mon:05:00-mon:06:00",
            # Note: transit_encryption_enabled is only supported on ReplicationGroup,
            # not CfnCacheCluster. Security is enforced via private subnet + SG.
            # Auto minor version upgrade
            auto_minor_version_upgrade=True,
        )
        redis_cluster.add_dependency(subnet_group)

        # ── Expose outputs ────────────────────────────────────────────────────
        self.redis_host = redis_cluster.attr_redis_endpoint_address
        self.redis_port = redis_cluster.attr_redis_endpoint_port

        # ── Outputs ───────────────────────────────────────────────────────────
        CfnOutput(
            self, "RedisEndpoint",
            value=self.redis_host,
            export_name=f"AcollyaRedisEndpoint-{stage}",
        )
        CfnOutput(
            self, "RedisPort",
            value=self.redis_port,
            export_name=f"AcollyaRedisPort-{stage}",
        )
