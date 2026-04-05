"""
VPC Stack — Network foundation for all Acollya services.

Design:
  - 2 Availability Zones (sa-east-1a, sa-east-1b)
  - Public subnets: for NAT Gateway only
  - Private subnets with egress: Lambda, RDS, Redis
  - Single NAT Gateway (cost optimization — ~R$170/mo at launch)
  - VPC Endpoints for S3 and Secrets Manager (reduces NAT data costs)

Cost at Phase 0:
  - NAT Gateway: ~$0.045/hr fixed + $0.045/GB processed ≈ $32/month
  - VPC Endpoints: $0.01/hr each ≈ $7/month for 2 endpoints
"""
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    CfnOutput,
)
from constructs import Construct


class VpcStack(Stack):
    def __init__(self, scope: Construct, id: str, stage: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.stage = stage

        # ── VPC ─────────────────────────────────────────────────────────────
        self.vpc = ec2.Vpc(
            self, "AcollyaVpc",
            vpc_name=f"acollya-vpc-{stage}",
            max_azs=2,
            nat_gateways=1,  # Single NAT — cost optimization for early stage
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
            ],
            enable_dns_hostnames=True,
            enable_dns_support=True,
        )

        # ── VPC Endpoints (reduce NAT Gateway costs) ─────────────────────────
        # S3 Gateway endpoint — free, routes S3 traffic directly (no NAT)
        self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )

        # Secrets Manager Interface endpoint — Lambda reads secrets without NAT
        self.vpc.add_interface_endpoint(
            "SecretsManagerEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
            private_dns_enabled=True,
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
        )

        # ── Security Groups ───────────────────────────────────────────────────

        # Lambda SG — outbound only (DB and Redis SGs will allow inbound from this)
        self.lambda_sg = ec2.SecurityGroup(
            self, "LambdaSg",
            vpc=self.vpc,
            security_group_name=f"acollya-lambda-sg-{stage}",
            description="Acollya Lambda functions",
            allow_all_outbound=True,
        )

        # ── Outputs ───────────────────────────────────────────────────────────
        # Note: DB and Redis SGs are created by their respective stacks
        # to avoid name conflicts. Only lambda_sg is shared via output.
        CfnOutput(self, "VpcId", value=self.vpc.vpc_id, export_name=f"AcollyaVpcId-{stage}")
        CfnOutput(self, "LambdaSgId", value=self.lambda_sg.security_group_id, export_name=f"AcollyaLambdaSgId-{stage}")
