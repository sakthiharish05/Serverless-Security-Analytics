"""
SNS-compatible notification and alerting abstraction.

Provides a unified interface for publishing security alerts,
with implementations for both local logging and AWS SNS.
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class NotificationClient(ABC):
    """Abstract base class for SNS-like notification service."""

    @abstractmethod
    def publish(self, subject: str, message: str, severity: str = "INFO",
                attributes: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Publish a notification/alert. Returns publish metadata."""
        pass

    @abstractmethod
    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alert history."""
        pass

    @abstractmethod
    def get_alert_count(self) -> int:
        """Get total number of alerts sent."""
        pass


class LocalNotificationClient(NotificationClient):
    """
    Local implementation of SNS-like notifications.

    Logs alerts to a JSON file and prints to console.
    Simulates SNS message publishing for local development.
    """

    def __init__(self, log_path: str):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.write_text("[]", encoding="utf-8")

    def _load_alerts(self) -> List[Dict[str, Any]]:
        """Load alert history from JSON file."""
        try:
            return json.loads(self.log_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_alerts(self, alerts: List[Dict[str, Any]]) -> None:
        """Save alert history to JSON file."""
        self.log_path.write_text(
            json.dumps(alerts, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def publish(self, subject: str, message: str, severity: str = "INFO",
                attributes: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Publish an alert to local storage."""
        alert = {
            "id": f"alert-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
            "subject": subject,
            "message": message,
            "severity": severity,
            "attributes": attributes or {},
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "delivered",
            "provider": "local",
            "topic": "local://SecurityAlerts",
        }

        # Console output with severity-based formatting
        severity_icons = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🟢",
            "INFO": "🔵",
        }
        icon = severity_icons.get(severity, "⚪")
        print(f"\n{icon} [SNS ALERT - {severity}] {subject}")
        print(f"   Message: {message}")
        if attributes:
            print(f"   Attributes: {json.dumps(attributes)}")
        print()

        # Persist to file
        alerts = self._load_alerts()
        alerts.insert(0, alert)  # Most recent first

        # Keep last 500 alerts
        alerts = alerts[:500]
        self._save_alerts(alerts)

        return {
            "message_id": alert["id"],
            "status": "delivered",
            "provider": "local",
        }

    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alerts from local storage."""
        alerts = self._load_alerts()
        return alerts[:limit]

    def get_alert_count(self) -> int:
        """Get total number of alerts."""
        return len(self._load_alerts())


class SNSNotificationClient(NotificationClient):
    """
    AWS SNS implementation of notification service.

    Uses boto3 to publish messages to real SNS topics.
    Requires valid AWS credentials and an existing SNS topic.
    """

    def __init__(self, topic_arn: str, region: str = "us-east-1"):
        import boto3
        self.topic_arn = topic_arn
        self.sns = boto3.client("sns", region_name=region)
        self._alert_history: List[Dict[str, Any]] = []

    def publish(self, subject: str, message: str, severity: str = "INFO",
                attributes: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Publish an alert to AWS SNS."""
        try:
            msg_attributes = {
                "severity": {
                    "DataType": "String",
                    "StringValue": severity,
                },
            }
            if attributes:
                for key, value in attributes.items():
                    msg_attributes[key] = {
                        "DataType": "String",
                        "StringValue": str(value),
                    }

            response = self.sns.publish(
                TopicArn=self.topic_arn,
                Subject=subject[:100],  # SNS subject max 100 chars
                Message=message,
                MessageAttributes=msg_attributes,
            )

            alert_record = {
                "id": response["MessageId"],
                "subject": subject,
                "message": message,
                "severity": severity,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "status": "delivered",
                "provider": "aws-sns",
                "topic": self.topic_arn,
            }
            self._alert_history.insert(0, alert_record)

            return {
                "message_id": response["MessageId"],
                "status": "delivered",
                "provider": "aws-sns",
            }
        except Exception as e:
            print(f"SNS publish error: {e}")
            return {
                "message_id": None,
                "status": "failed",
                "error": str(e),
            }

    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alerts (from in-memory history for SNS)."""
        return self._alert_history[:limit]

    def get_alert_count(self) -> int:
        """Get total alerts sent in this session."""
        return len(self._alert_history)
