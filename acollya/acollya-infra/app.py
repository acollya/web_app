#!/usr/bin/env python3
"""
Acollya Infrastructure — AWS CDK App Entry Point

Deploy commands:
  cdk deploy --all --context stage=dev --context account=<AWS_ACCOUNT_ID>
  cdk deploy --all --context stage=prod --context account=<AWS_ACCOUNT_ID>
"""
import aws_cdk as cdk

from stacks.vpc_stack import VpcStack
from stacks.database_stack import DatabaseStack
from stacks.cache_stack import CacheStack
from stacks.storage_stack import StorageStack
from stacks.secrets_stack import SecretsStack
from stacks.api_stack import ApiStack
from stacks.jobs_stack import JobsStack
from stacks.monitoring_stack import MonitoringStack

app = cdk.App()

# --- Context ---
account = app.node.try_get_context("account")
region = app.node.try_get_context("region") or "sa-east-1"  # São Paulo — LGPD compliance
stage = app.node.try_get_context("stage") or "dev"

env = cdk.Environment(account=account, region=region)

# --- Tags applied to every resource ---
tags = {
    "Project": "Acollya",
    "Stage": stage,
    "ManagedBy": "CDK",
}

# ── Stacks ──────────────────────────────────────────────────────────────────

vpc_stack = VpcStack(app, f"AcollyaVpc-{stage}", env=env, stage=stage)

secrets_stack = SecretsStack(app, f"AcollyaSecrets-{stage}", env=env, stage=stage)

db_stack = DatabaseStack(
    app, f"AcollyaDatabase-{stage}",
    vpc=vpc_stack.vpc,
    lambda_sg=vpc_stack.lambda_sg,
    env=env,
    stage=stage,
)
db_stack.add_dependency(vpc_stack)

cache_stack = CacheStack(
    app, f"AcollyaCache-{stage}",
    vpc=vpc_stack.vpc,
    lambda_sg=vpc_stack.lambda_sg,
    env=env,
    stage=stage,
)
cache_stack.add_dependency(vpc_stack)

storage_stack = StorageStack(app, f"AcollyaStorage-{stage}", env=env, stage=stage)

api_stack = ApiStack(
    app, f"AcollyaApi-{stage}",
    vpc=vpc_stack.vpc,
    lambda_sg=vpc_stack.lambda_sg,
    db_secret=db_stack.db_secret,
    db_host=db_stack.proxy_endpoint,  # Lambda connects via RDS Proxy
    redis_host=cache_stack.redis_host,
    redis_port=cache_stack.redis_port,
    redis_tls=cache_stack.redis_tls,   # Always True — TLS enforced at infra level
    media_bucket=storage_stack.media_bucket,
    env=env,
    stage=stage,
)
api_stack.add_dependency(db_stack)
api_stack.add_dependency(cache_stack)
api_stack.add_dependency(storage_stack)
api_stack.add_dependency(secrets_stack)

# ── Scheduled background jobs (EventBridge cron Lambdas) ────────────────────
# Runs alongside ApiStack — separate stack so cron lifecycle doesn't couple
# to the user-facing API deploys/rollbacks.
jobs_stack = JobsStack(
    app, f"AcollyaJobs-{stage}",
    vpc=vpc_stack.vpc,
    lambda_sg=vpc_stack.lambda_sg,
    db_secret=db_stack.db_secret,
    db_host=db_stack.proxy_endpoint,
    redis_host=cache_stack.redis_host,
    redis_port=cache_stack.redis_port,
    redis_tls=cache_stack.redis_tls,
    media_bucket=storage_stack.media_bucket,
    env=env,
    stage=stage,
)
jobs_stack.add_dependency(db_stack)
jobs_stack.add_dependency(cache_stack)
jobs_stack.add_dependency(storage_stack)
jobs_stack.add_dependency(secrets_stack)

monitoring_stack = MonitoringStack(
    app, f"AcollyaMonitoring-{stage}",
    api_lambda=api_stack.api_lambda,
    chat_lambda=api_stack.chat_lambda,
    db_instance=db_stack.db_instance,
    api_gateway_id=api_stack.http_api_id,
    ops_email=app.node.try_get_context("ops_email") or "",
    env=env,
    stage=stage,
)
monitoring_stack.add_dependency(api_stack)

# Apply tags to all stacks
for key, value in tags.items():
    cdk.Tags.of(app).add(key, value)

app.synth()
