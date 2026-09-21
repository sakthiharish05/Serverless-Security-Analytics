"""
Cloud provider configuration.

Reads environment variables to determine which cloud backend to use
and provides centralized configuration for all cloud services.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CloudConfig:
    """Configuration for cloud service backends."""

    # Provider: "local" or "aws"
    provider: str = "local"

    # AWS Configuration
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # S3 Configuration
    s3_bucket: str = "security-logs-bucket"
    s3_local_path: str = ""  # Set in __post_init__

    # DynamoDB Configuration
    dynamodb_table_incidents: str = "SecurityIncidents"
    dynamodb_table_analysis: str = "AnalysisHistory"
    dynamodb_local_db_path: str = ""  # Set in __post_init__

    # SNS Configuration
    sns_topic_arn: str = "arn:aws:sns:us-east-1:000000000000:SecurityAlerts"
    sns_local_log_path: str = ""  # Set in __post_init__

    # CloudWatch Configuration
    cloudwatch_log_group: str = "/security/application-logs"
    cloudwatch_local_path: str = ""  # Set in __post_init__

    def __post_init__(self):
        """Set default local paths relative to project data directory."""
        data_dir = Path(__file__).resolve().parent.parent.parent / "data"

        if not self.s3_local_path:
            self.s3_local_path = str(data_dir / "s3_storage")
        if not self.dynamodb_local_db_path:
            self.dynamodb_local_db_path = str(data_dir / "dynamodb.sqlite")
        if not self.sns_local_log_path:
            self.sns_local_log_path = str(data_dir / "sns_alerts.json")
        if not self.cloudwatch_local_path:
            self.cloudwatch_local_path = str(data_dir / "log_sources")


def get_cloud_config() -> CloudConfig:
    """
    Build configuration from environment variables.

    Environment Variables:
        CLOUD_PROVIDER: "local" (default) or "aws"
        AWS_REGION: AWS region (default: us-east-1)
        AWS_ACCESS_KEY_ID: AWS access key
        AWS_SECRET_ACCESS_KEY: AWS secret key
        S3_BUCKET: S3 bucket name
        DYNAMODB_TABLE_INCIDENTS: DynamoDB table for incidents
        DYNAMODB_TABLE_ANALYSIS: DynamoDB table for analysis history
        SNS_TOPIC_ARN: SNS topic ARN for alerts
        CLOUDWATCH_LOG_GROUP: CloudWatch log group to ingest from
    """
    return CloudConfig(
        provider=os.environ.get("CLOUD_PROVIDER", "local").lower(),
        aws_region=os.environ.get("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", ""),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
        s3_bucket=os.environ.get("S3_BUCKET", "security-logs-bucket"),
        dynamodb_table_incidents=os.environ.get("DYNAMODB_TABLE_INCIDENTS", "SecurityIncidents"),
        dynamodb_table_analysis=os.environ.get("DYNAMODB_TABLE_ANALYSIS", "AnalysisHistory"),
        sns_topic_arn=os.environ.get("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:000000000000:SecurityAlerts"),
        cloudwatch_log_group=os.environ.get("CLOUDWATCH_LOG_GROUP", "/security/application-logs"),
    )
