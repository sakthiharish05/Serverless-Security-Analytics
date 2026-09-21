"""
CloudWatch-compatible log source abstraction.

Provides a unified interface for fetching logs from external sources,
with implementations for both local files and AWS CloudWatch Logs.
"""

import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class LogSourceClient(ABC):
    """Abstract base class for CloudWatch-like log source."""

    @abstractmethod
    def list_log_groups(self) -> List[Dict[str, Any]]:
        """List available log groups/sources."""
        pass

    @abstractmethod
    def fetch_log_events(self, log_group: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch log events from a log group. Returns list of log entries."""
        pass

    @abstractmethod
    def get_log_group_info(self, log_group: str) -> Optional[Dict[str, Any]]:
        """Get metadata about a log group."""
        pass


class LocalLogSourceClient(LogSourceClient):
    """
    Local filesystem implementation of CloudWatch-like log sources.

    Uses a directory structure to simulate CloudWatch log groups:
    - Each subdirectory = a log group
    - Each .log file in the subdirectory = log events
    
    Pre-populated with sample log files for demonstration.
    """

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._ensure_sample_logs()

    def _ensure_sample_logs(self):
        """Create sample log groups and files if none exist."""
        if any(self.base_path.iterdir()):
            return

        # Sample: Web Application Logs
        web_logs_dir = self.base_path / "web-application"
        web_logs_dir.mkdir(exist_ok=True)
        (web_logs_dir / "access.log").write_text(
            """2026-09-01T10:00:01Z 192.168.1.50 GET /api/users?id=1 OR 1=1 HTTP/1.1 200 3412
2026-09-01T10:00:05Z 192.168.1.51 POST /login HTTP/1.1 401 auth failed user=admin
2026-09-01T10:00:06Z 192.168.1.51 POST /login HTTP/1.1 401 auth failed user=admin
2026-09-01T10:00:07Z 192.168.1.51 POST /login HTTP/1.1 401 auth failed user=admin
2026-09-01T10:00:08Z 192.168.1.51 POST /login HTTP/1.1 401 auth failed user=admin
2026-09-01T10:00:15Z 192.168.1.52 GET /dashboard HTTP/1.1 200 8192
2026-09-01T10:01:30Z 10.0.0.5 GET /api/data HTTP/1.1 200 1024
2026-09-01T10:02:45Z 192.168.1.53 POST /search HTTP/1.1 200 2048 query=<script>alert('xss')</script>
""",
            encoding="utf-8",
        )

        # Sample: Authentication Logs
        auth_logs_dir = self.base_path / "auth-service"
        auth_logs_dir.mkdir(exist_ok=True)
        (auth_logs_dir / "auth.log").write_text(
            """2026-09-01T09:30:00Z [INFO] user=alice ip=10.0.0.2 action=login status=success
2026-09-01T09:31:00Z [WARN] user=bob ip=192.168.1.100 action=login status=failed reason="invalid password"
2026-09-01T09:31:05Z [WARN] user=bob ip=192.168.1.100 action=login status=failed reason="invalid password"
2026-09-01T09:31:10Z [WARN] user=bob ip=192.168.1.100 action=login status=failed reason="invalid password"
2026-09-01T09:32:00Z [ALERT] user=root ip=203.0.113.50 action=sudo command="cat /etc/shadow"
2026-09-01T09:33:00Z [INFO] user=admin ip=10.0.0.1 action=privilege_escalation role=superuser
2026-09-01T09:34:00Z [WARN] user=unknown ip=198.51.100.23 action=login status=failed reason="user not found"
""",
            encoding="utf-8",
        )

        # Sample: Database Logs
        db_logs_dir = self.base_path / "database-server"
        db_logs_dir.mkdir(exist_ok=True)
        (db_logs_dir / "queries.log").write_text(
            """2026-09-01T08:00:00Z [QUERY] user=app_user db=production query="SELECT * FROM users WHERE id=1"
2026-09-01T08:05:00Z [QUERY] user=app_user db=production query="SELECT * FROM products WHERE name LIKE '%phone%'"
2026-09-01T08:10:00Z [SLOW_QUERY] user=report_user db=production query="SELECT * FROM orders JOIN users" duration=5200ms
2026-09-01T08:15:00Z [ALERT] user=unknown db=production query="SELECT * FROM users UNION ALL SELECT password FROM credentials"
2026-09-01T08:20:00Z [ALERT] user=unknown db=production query="DROP TABLE sessions; --"
2026-09-01T08:25:00Z [QUERY] user=backup_svc db=production query="INFORMATION_SCHEMA.TABLES"
""",
            encoding="utf-8",
        )

    def list_log_groups(self) -> List[Dict[str, Any]]:
        """List available log groups (local directories)."""
        groups = []
        for path in sorted(self.base_path.iterdir()):
            if path.is_dir() and not path.name.startswith("."):
                # Count log files and total size
                log_files = list(path.glob("*.log"))
                total_size = sum(f.stat().st_size for f in log_files)
                latest_modified = max(
                    (f.stat().st_mtime for f in log_files), default=0
                )

                groups.append({
                    "name": path.name,
                    "arn": f"arn:aws:logs:local:000000000000:log-group:/{path.name}",
                    "log_file_count": len(log_files),
                    "total_size_bytes": total_size,
                    "last_event_time": datetime.fromtimestamp(latest_modified).isoformat() + "Z" if latest_modified else None,
                    "provider": "local",
                })

        return groups

    def fetch_log_events(self, log_group: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch log events from a local log group directory."""
        group_path = self.base_path / log_group
        if not group_path.exists() or not group_path.is_dir():
            return []

        events = []
        for log_file in sorted(group_path.glob("*.log")):
            try:
                content = log_file.read_text(encoding="utf-8")
                for line_num, line in enumerate(content.strip().split("\n"), 1):
                    line = line.strip()
                    if line:
                        events.append({
                            "log_group": log_group,
                            "log_stream": log_file.name,
                            "message": line,
                            "line_number": line_num,
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "ingestion_time": datetime.utcnow().isoformat() + "Z",
                        })
            except Exception as e:
                print(f"Error reading {log_file}: {e}")

        return events[:limit]

    def get_log_group_info(self, log_group: str) -> Optional[Dict[str, Any]]:
        """Get metadata about a local log group."""
        group_path = self.base_path / log_group
        if not group_path.exists():
            return None

        log_files = list(group_path.glob("*.log"))
        total_size = sum(f.stat().st_size for f in log_files)
        total_lines = 0
        for f in log_files:
            try:
                total_lines += sum(1 for line in f.read_text(encoding="utf-8").strip().split("\n") if line.strip())
            except Exception:
                pass

        return {
            "name": log_group,
            "arn": f"arn:aws:logs:local:000000000000:log-group:/{log_group}",
            "log_file_count": len(log_files),
            "total_events": total_lines,
            "total_size_bytes": total_size,
            "provider": "local",
        }


class CloudWatchClient(LogSourceClient):
    """
    AWS CloudWatch Logs implementation.

    Uses boto3 to fetch logs from real CloudWatch Log Groups.
    Requires valid AWS credentials and existing log groups.
    """

    def __init__(self, region: str = "us-east-1"):
        import boto3
        self.logs_client = boto3.client("logs", region_name=region)

    def list_log_groups(self) -> List[Dict[str, Any]]:
        """List CloudWatch log groups."""
        try:
            response = self.logs_client.describe_log_groups(limit=50)
            groups = []
            for group in response.get("logGroups", []):
                groups.append({
                    "name": group["logGroupName"],
                    "arn": group.get("arn", ""),
                    "stored_bytes": group.get("storedBytes", 0),
                    "last_event_time": datetime.fromtimestamp(
                        group.get("creationTime", 0) / 1000
                    ).isoformat() + "Z",
                    "provider": "aws-cloudwatch",
                })
            return groups
        except Exception as e:
            print(f"CloudWatch list_log_groups error: {e}")
            return []

    def fetch_log_events(self, log_group: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch recent log events from CloudWatch."""
        try:
            response = self.logs_client.filter_log_events(
                logGroupName=log_group,
                limit=limit,
                interleaved=True,
            )
            events = []
            for event in response.get("events", []):
                events.append({
                    "log_group": log_group,
                    "log_stream": event.get("logStreamName", ""),
                    "message": event.get("message", ""),
                    "timestamp": datetime.fromtimestamp(
                        event.get("timestamp", 0) / 1000
                    ).isoformat() + "Z",
                    "ingestion_time": datetime.fromtimestamp(
                        event.get("ingestionTime", 0) / 1000
                    ).isoformat() + "Z",
                    "event_id": event.get("eventId", ""),
                })
            return events
        except Exception as e:
            print(f"CloudWatch fetch error: {e}")
            return []

    def get_log_group_info(self, log_group: str) -> Optional[Dict[str, Any]]:
        """Get CloudWatch log group metadata."""
        try:
            response = self.logs_client.describe_log_groups(
                logGroupNamePrefix=log_group,
                limit=1,
            )
            groups = response.get("logGroups", [])
            if groups:
                group = groups[0]
                return {
                    "name": group["logGroupName"],
                    "arn": group.get("arn", ""),
                    "stored_bytes": group.get("storedBytes", 0),
                    "provider": "aws-cloudwatch",
                }
            return None
        except Exception:
            return None
