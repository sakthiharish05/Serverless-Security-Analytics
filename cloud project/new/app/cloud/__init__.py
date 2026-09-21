"""
Cloud service abstraction layer.

Provides pluggable backends for AWS services (S3, DynamoDB, SNS, CloudWatch)
with local implementations for development and real AWS implementations for production.

Switch between modes via CLOUD_PROVIDER environment variable:
  - "local" (default): Uses filesystem, SQLite, and console logging
  - "aws": Uses real AWS services via boto3
"""

from app.cloud.config import get_cloud_config, CloudConfig
