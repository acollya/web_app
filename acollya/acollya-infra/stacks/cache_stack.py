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

TLS:
  CfnCacheCluster does NOT support transit_encryption_enabled.
  We use CfnReplicationGroup (single-node, no failover) which supports TLS.
  Lambda connects via rediss:// when REDIS_TLS=true (set by ApiStack for prod).
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

        # ── Redis Replication Group (single-node, TLS enabled) ────────────────
        # CfnReplicationGroup is required for transit_encryption_enabled.
        # num_cache_clusters=1 + automatic_failover_enabled=False = single node.
        redis = elasticache.CfnReplicationGroup(
            self, "AcollyaRedis",
            replication_group_description=f"Acollya Redis - {stage}",
            replication_group_id=f"acollya-redis-{stage}",
            cache_node_type="cache.t3.micro" if not is_prod else "cache.t3.small",
            engine="redis",
            engine_version="7.1",
            num_cache_clusters=1,
            automatic_failover_enabled=False,  # required when num_cache_clusters=1
            multi_az_enabled=False,
            cache_subnet_group_name=subnet_group.cache_subnet_group_name,
            security_group_ids=[redis_sg.security_group_id],
            # Encryption
            at_rest_encryption_enabled=True,
            transit_encryption_enabled=True,
            # Persistence — RDB snapshot every 12h
            snapshot_retention_limit=1 if not is_prod else 3,
            snapshot_window="02:00-03:00",
            preferred_maintenance_window="mon:05:00-mon:06:00",
            auto_minor_version_upgrade=True,
        )
        redis.add_dependency(subnet_group)

        # ── Expose outputs ────────────────────────────────────────────────────
        # ReplicationGroup primary endpoint (not attr_redis_endpoint_address)
        self.redis_host = redis.attr_primary_end_point_address
        self.redis_port = redis.attr_primary_end_point_port
        self.redis_tls = True  # Always TLS — Lambda reads this to use rediss://

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
