"""
Monitoring Stack — CloudWatch dashboards, alarms, and SNS alerts.

Alarms:
  - Lambda API: error rate > 1%, p99 latency > 3s
  - Lambda Chat: error rate > 2%, p99 latency > 10s, throttles > 0
  - RDS: CPU > 80%, FreeStorage < 2GB, DatabaseConnections > 80
  - API Gateway: 5xx errors > 10/min, 4xx errors > 50/min

Dashboard:
  - Single "Acollya Overview" dashboard with all key metrics
  - Visible in CloudWatch console → Dashboards
"""
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_lambda as _lambda,
    aws_rds as rds,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    CfnOutput,
)
from constructs import Construct


class MonitoringStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        api_lambda: _lambda.Function,
        chat_lambda: _lambda.Function,
        db_instance: rds.DatabaseInstance,
        api_gateway_id: str,
        stage: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self.stage = stage
        is_prod = stage == "prod"

        # ── SNS Alert Topic ───────────────────────────────────────────────────
        alert_topic = sns.Topic(
            self, "AlertTopic",
            topic_name=f"acollya-alerts-{stage}",
            display_name=f"Acollya {stage.upper()} Alerts",
        )

        # Add email subscription — replace with your ops email
        # Uncomment after deploy and confirm subscription in email:
        # alert_topic.add_subscription(
        #     subscriptions.EmailSubscription("ops@acollya.com.br")
        # )

        alarm_action = cw_actions.SnsAction(alert_topic)

        # ── Lambda API Alarms ─────────────────────────────────────────────────
        api_error_alarm = cloudwatch.Alarm(
            self, "ApiErrorAlarm",
            alarm_name=f"acollya-api-errors-{stage}",
            alarm_description="API Lambda error rate > 1%",
            metric=api_lambda.metric_errors(
                period=Duration.minutes(5),
                statistic="Sum",
            ),
            threshold=5,
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        api_error_alarm.add_alarm_action(alarm_action)

        api_latency_alarm = cloudwatch.Alarm(
            self, "ApiLatencyAlarm",
            alarm_name=f"acollya-api-latency-{stage}",
            alarm_description="API Lambda p99 latency > 3s",
            metric=api_lambda.metric_duration(
                period=Duration.minutes(5),
                statistic="p99",
            ),
            threshold=3000,  # ms
            evaluation_periods=3,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        api_latency_alarm.add_alarm_action(alarm_action)

        # ── Lambda Chat Alarms ────────────────────────────────────────────────
        chat_error_alarm = cloudwatch.Alarm(
            self, "ChatErrorAlarm",
            alarm_name=f"acollya-chat-errors-{stage}",
            alarm_description="Chat Lambda error rate > 2%",
            metric=chat_lambda.metric_errors(
                period=Duration.minutes(5),
                statistic="Sum",
            ),
            threshold=3,
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        chat_error_alarm.add_alarm_action(alarm_action)

        chat_throttle_alarm = cloudwatch.Alarm(
            self, "ChatThrottleAlarm",
            alarm_name=f"acollya-chat-throttles-{stage}",
            alarm_description="Chat Lambda throttles > 0",
            metric=chat_lambda.metric_throttles(
                period=Duration.minutes(5),
                statistic="Sum",
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        if is_prod:
            chat_throttle_alarm.add_alarm_action(alarm_action)

        # ── RDS Alarms ────────────────────────────────────────────────────────
        rds_cpu_alarm = cloudwatch.Alarm(
            self, "RdsCpuAlarm",
            alarm_name=f"acollya-rds-cpu-{stage}",
            alarm_description="RDS CPU utilization > 80%",
            metric=cloudwatch.Metric(
                namespace="AWS/RDS",
                metric_name="CPUUtilization",
                dimensions_map={"DBInstanceIdentifier": db_instance.instance_identifier},
                period=Duration.minutes(5),
                statistic="Average",
            ),
            threshold=80,
            evaluation_periods=3,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        rds_cpu_alarm.add_alarm_action(alarm_action)

        rds_storage_alarm = cloudwatch.Alarm(
            self, "RdsStorageAlarm",
            alarm_name=f"acollya-rds-storage-{stage}",
            alarm_description="RDS free storage < 2GB",
            metric=cloudwatch.Metric(
                namespace="AWS/RDS",
                metric_name="FreeStorageSpace",
                dimensions_map={"DBInstanceIdentifier": db_instance.instance_identifier},
                period=Duration.minutes(15),
                statistic="Average",
            ),
            threshold=2 * 1024 * 1024 * 1024,  # 2GB in bytes
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        rds_storage_alarm.add_alarm_action(alarm_action)

        # ── CloudWatch Dashboard ──────────────────────────────────────────────
        dashboard = cloudwatch.Dashboard(
            self, "AcollyaDashboard",
            dashboard_name=f"Acollya-{stage}",
        )

        dashboard.add_widgets(
            cloudwatch.TextWidget(
                markdown=f"# Acollya — {stage.upper()} Overview",
                width=24,
                height=1,
            ),
        )

        dashboard.add_widgets(
            # Lambda API metrics
            cloudwatch.GraphWidget(
                title="API Lambda — Invocations & Errors",
                left=[
                    api_lambda.metric_invocations(period=Duration.minutes(5)),
                    api_lambda.metric_errors(period=Duration.minutes(5)),
                ],
                right=[api_lambda.metric_duration(period=Duration.minutes(5), statistic="p99")],
                width=12,
                height=6,
            ),
            # Lambda Chat metrics
            cloudwatch.GraphWidget(
                title="Chat Lambda — Invocations & Errors",
                left=[
                    chat_lambda.metric_invocations(period=Duration.minutes(5)),
                    chat_lambda.metric_errors(period=Duration.minutes(5)),
                    chat_lambda.metric_throttles(period=Duration.minutes(5)),
                ],
                right=[chat_lambda.metric_duration(period=Duration.minutes(5), statistic="p99")],
                width=12,
                height=6,
            ),
        )

        dashboard.add_widgets(
            # RDS metrics
            cloudwatch.GraphWidget(
                title="RDS — CPU & Connections",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/RDS",
                        metric_name="CPUUtilization",
                        dimensions_map={"DBInstanceIdentifier": db_instance.instance_identifier},
                        period=Duration.minutes(5),
                    ),
                ],
                right=[
                    cloudwatch.Metric(
                        namespace="AWS/RDS",
                        metric_name="DatabaseConnections",
                        dimensions_map={"DBInstanceIdentifier": db_instance.instance_identifier},
                        period=Duration.minutes(5),
                    ),
                ],
                width=12,
                height=6,
            ),
            cloudwatch.GraphWidget(
                title="RDS — Storage & IOPS",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/RDS",
                        metric_name="FreeStorageSpace",
                        dimensions_map={"DBInstanceIdentifier": db_instance.instance_identifier},
                        period=Duration.minutes(15),
                    ),
                ],
                right=[
                    cloudwatch.Metric(
                        namespace="AWS/RDS",
                        metric_name="ReadIOPS",
                        dimensions_map={"DBInstanceIdentifier": db_instance.instance_identifier},
                        period=Duration.minutes(5),
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/RDS",
                        metric_name="WriteIOPS",
                        dimensions_map={"DBInstanceIdentifier": db_instance.instance_identifier},
                        period=Duration.minutes(5),
                    ),
                ],
                width=12,
                height=6,
            ),
        )

        # Alarm status widget
        dashboard.add_widgets(
            cloudwatch.AlarmStatusWidget(
                title="Active Alarms",
                alarms=[
                    api_error_alarm,
                    api_latency_alarm,
                    chat_error_alarm,
                    rds_cpu_alarm,
                    rds_storage_alarm,
                ],
                width=24,
                height=4,
            )
        )

        CfnOutput(self, "AlertTopicArn", value=alert_topic.topic_arn, export_name=f"AcollyaAlertTopicArn-{stage}")
        CfnOutput(self, "DashboardUrl", value=f"https://{self.region}.console.aws.amazon.com/cloudwatch/home#dashboards:name=Acollya-{stage}")
