"""
Event-Driven Security Processing Pipeline.

Orchestrates the cloud-native security analysis workflow:
  Upload/Ingest → Store (S3) → Analyze → Store Results (DynamoDB) → Alert (SNS)

This is the core engine that ties all cloud services together.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.analyzer import detect_threat
from app.cloud.config import CloudConfig, get_cloud_config
from app.cloud.storage import LocalStorageClient, S3StorageClient, StorageClient
from app.cloud.database import LocalDatabaseClient, DynamoDBClient, DatabaseClient
from app.cloud.notifications import LocalNotificationClient, SNSNotificationClient, NotificationClient
from app.cloud.log_source import LocalLogSourceClient, CloudWatchClient, LogSourceClient


class SecurityPipeline:
    """
    Cloud-native security processing pipeline.

    Connects storage (S3), database (DynamoDB), notifications (SNS),
    and log sources (CloudWatch) into an event-driven analysis workflow.
    """

    # DynamoDB table names
    TABLE_INCIDENTS = "SecurityIncidents"
    TABLE_ANALYSIS = "AnalysisHistory"

    def __init__(self, config: Optional[CloudConfig] = None):
        self.config = config or get_cloud_config()
        self.storage: StorageClient
        self.database: DatabaseClient
        self.notifications: NotificationClient
        self.log_source: LogSourceClient

        self._init_services()

        # Pipeline statistics
        self._stats = {
            "total_logs_processed": 0,
            "total_threats_detected": 0,
            "total_alerts_sent": 0,
            "pipeline_start_time": datetime.utcnow().isoformat() + "Z",
        }

    def _init_services(self):
        """Initialize cloud service clients based on provider configuration."""
        if self.config.provider == "aws":
            self.storage = S3StorageClient(
                bucket_name=self.config.s3_bucket,
                region=self.config.aws_region,
            )
            self.database = DynamoDBClient(region=self.config.aws_region)
            self.notifications = SNSNotificationClient(
                topic_arn=self.config.sns_topic_arn,
                region=self.config.aws_region,
            )
            self.log_source = CloudWatchClient(region=self.config.aws_region)
        else:
            # Local implementations
            self.storage = LocalStorageClient(self.config.s3_local_path)
            self.database = LocalDatabaseClient(self.config.dynamodb_local_db_path)
            self.notifications = LocalNotificationClient(self.config.sns_local_log_path)
            self.log_source = LocalLogSourceClient(self.config.cloudwatch_local_path)

    # ──────────────────────────────────────────────────────────
    # Core Pipeline Operations
    # ──────────────────────────────────────────────────────────

    def process_uploaded_log(self, filename: str, content: bytes) -> Dict[str, Any]:
        """
        Full pipeline: Upload → Store in S3 → Analyze → Store Results → Alert.

        This simulates the event-driven flow:
        1. Log file lands in S3
        2. S3 event triggers Lambda
        3. Lambda analyzes the log
        4. Results stored in DynamoDB
        5. If critical, alert via SNS

        Args:
            filename: Name of the uploaded log file
            content: Raw log file content as bytes

        Returns:
            Pipeline execution result with analysis and storage metadata
        """
        pipeline_id = f"pipe-{uuid.uuid4().hex[:8]}"
        started_at = datetime.utcnow().isoformat() + "Z"

        result = {
            "pipeline_id": pipeline_id,
            "filename": filename,
            "started_at": started_at,
            "stages": {},
        }

        try:
            # ── Stage 1: Store in S3 ──
            s3_key = f"uploads/{datetime.utcnow().strftime('%Y/%m/%d')}/{pipeline_id}/{filename}"
            upload_result = self.storage.upload_object(
                key=s3_key,
                data=content,
                metadata={
                    "content_type": "text/plain",
                    "pipeline_id": pipeline_id,
                    "source": "web-upload",
                },
            )
            result["stages"]["s3_upload"] = {
                "status": "success",
                "key": s3_key,
                "size": len(content),
                "location": upload_result.get("location", ""),
            }

            # ── Stage 2: Analyze ──
            log_text = content.decode("utf-8", errors="replace")
            analysis = detect_threat(log_text)
            result["stages"]["analysis"] = {
                "status": "success",
                "threat_status": analysis.get("status"),
                "severity": analysis.get("severity", "LOW"),
                "matched_rules_count": len(analysis.get("matchedRules", [])),
                "analysis_result": analysis,
            }

            # ── Stage 3: Store in DynamoDB ──
            analysis_record = {
                "id": pipeline_id,
                "type": "analysis",
                "filename": filename,
                "s3_key": s3_key,
                "status": analysis.get("status"),
                "severity": analysis.get("severity", "LOW"),
                "threat_type": analysis.get("type", "none"),
                "matched_rules_count": len(analysis.get("matchedRules", [])),
                "matched_rules": [r.get("id", "") for r in analysis.get("matchedRules", [])],
                "source": "pipeline-upload",
                "processed_at": datetime.utcnow().isoformat() + "Z",
                "file_size_bytes": len(content),
            }
            self.database.put_item(self.TABLE_ANALYSIS, analysis_record)
            result["stages"]["dynamodb_store"] = {"status": "success", "table": self.TABLE_ANALYSIS}

            # ── Stage 4: Alert via SNS (if threats detected) ──
            if analysis.get("status") == "threat_detected":
                severity = analysis.get("severity", "MEDIUM")
                rules = analysis.get("matchedRules", [])
                rule_summary = ", ".join(r.get("type", "Unknown") for r in rules[:5])

                alert_result = self.notifications.publish(
                    subject=f"🚨 Security Threat Detected [{severity}]: {analysis.get('type', 'Unknown')}",
                    message=(
                        f"Pipeline {pipeline_id} detected threats in '{filename}'.\n"
                        f"Severity: {severity}\n"
                        f"Primary Threat: {analysis.get('type', 'Unknown')}\n"
                        f"Matched Rules ({len(rules)}): {rule_summary}\n"
                        f"S3 Location: {s3_key}\n"
                        f"Time: {datetime.utcnow().isoformat()}Z"
                    ),
                    severity=severity,
                    attributes={
                        "pipeline_id": pipeline_id,
                        "threat_type": analysis.get("type", "Unknown"),
                        "filename": filename,
                    },
                )
                result["stages"]["sns_alert"] = {
                    "status": "success",
                    "message_id": alert_result.get("message_id"),
                    "severity": severity,
                }
                self._stats["total_alerts_sent"] += 1

                # Auto-create incident for HIGH/CRITICAL threats
                if severity in ("HIGH", "CRITICAL"):
                    incident = self._auto_create_incident(
                        pipeline_id, filename, analysis, s3_key
                    )
                    result["stages"]["auto_incident"] = {
                        "status": "success",
                        "incident_id": incident.get("id"),
                    }
            else:
                result["stages"]["sns_alert"] = {"status": "skipped", "reason": "no threats detected"}

            # Update stats
            self._stats["total_logs_processed"] += 1
            if analysis.get("status") == "threat_detected":
                self._stats["total_threats_detected"] += 1

            result["status"] = "completed"
            result["completed_at"] = datetime.utcnow().isoformat() + "Z"

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            result["completed_at"] = datetime.utcnow().isoformat() + "Z"

        return result

    def ingest_from_cloud_source(self, log_group: str) -> Dict[str, Any]:
        """
        Pull logs from CloudWatch (or local source) and process through pipeline.

        Simulates: CloudWatch → Lambda Trigger → Analysis → DynamoDB + SNS

        Args:
            log_group: Name of the log group to ingest from

        Returns:
            Ingestion result with analysis summary
        """
        ingest_id = f"ingest-{uuid.uuid4().hex[:8]}"
        started_at = datetime.utcnow().isoformat() + "Z"

        result = {
            "ingest_id": ingest_id,
            "log_group": log_group,
            "started_at": started_at,
            "events_fetched": 0,
            "threats_found": 0,
            "analyses": [],
        }

        try:
            # Fetch log events from source
            events = self.log_source.fetch_log_events(log_group, limit=200)
            result["events_fetched"] = len(events)

            if not events:
                result["status"] = "completed"
                result["message"] = "No log events found in log group"
                return result

            # Combine all events into a single log blob for analysis
            combined_logs = "\n".join(e.get("message", "") for e in events if e.get("message"))

            # Store combined logs in S3
            s3_key = f"cloudwatch/{log_group}/{datetime.utcnow().strftime('%Y/%m/%d')}/{ingest_id}.log"
            self.storage.upload_object(
                key=s3_key,
                data=combined_logs.encode("utf-8"),
                metadata={
                    "content_type": "text/plain",
                    "source": "cloudwatch-ingest",
                    "log_group": log_group,
                    "ingest_id": ingest_id,
                },
            )

            # Analyze
            analysis = detect_threat(combined_logs)

            # Store analysis in DynamoDB
            analysis_record = {
                "id": ingest_id,
                "type": "cloudwatch_ingest",
                "log_group": log_group,
                "s3_key": s3_key,
                "status": analysis.get("status"),
                "severity": analysis.get("severity", "LOW"),
                "threat_type": analysis.get("type", "none"),
                "matched_rules_count": len(analysis.get("matchedRules", [])),
                "matched_rules": [r.get("id", "") for r in analysis.get("matchedRules", [])],
                "events_processed": len(events),
                "source": "cloudwatch-ingest",
                "processed_at": datetime.utcnow().isoformat() + "Z",
            }
            self.database.put_item(self.TABLE_ANALYSIS, analysis_record)

            # Alert if threats found
            if analysis.get("status") == "threat_detected":
                result["threats_found"] = len(analysis.get("matchedRules", []))
                severity = analysis.get("severity", "MEDIUM")

                self.notifications.publish(
                    subject=f"🔍 CloudWatch Ingest Alert [{severity}]: Threats in {log_group}",
                    message=(
                        f"Ingestion {ingest_id} found threats in CloudWatch log group '{log_group}'.\n"
                        f"Events analyzed: {len(events)}\n"
                        f"Threats found: {result['threats_found']}\n"
                        f"Severity: {severity}\n"
                        f"Primary Threat: {analysis.get('type', 'Unknown')}"
                    ),
                    severity=severity,
                    attributes={
                        "ingest_id": ingest_id,
                        "log_group": log_group,
                    },
                )
                self._stats["total_alerts_sent"] += 1
                self._stats["total_threats_detected"] += 1

            self._stats["total_logs_processed"] += 1

            result["analysis_summary"] = {
                "status": analysis.get("status"),
                "severity": analysis.get("severity"),
                "threat_type": analysis.get("type"),
                "matched_rules": len(analysis.get("matchedRules", [])),
                "analysis_result": analysis,
            }
            result["status"] = "completed"
            result["completed_at"] = datetime.utcnow().isoformat() + "Z"

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    # ──────────────────────────────────────────────────────────
    # Helper Methods
    # ──────────────────────────────────────────────────────────

    def _auto_create_incident(self, pipeline_id: str, filename: str,
                              analysis: Dict, s3_key: str) -> Dict[str, Any]:
        """Auto-create an incident in DynamoDB for high-severity threats."""
        incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.utcnow().isoformat() + "Z"

        rules = analysis.get("matchedRules", [])
        incident = {
            "id": incident_id,
            "title": f"[Auto] {analysis.get('type', 'Unknown Threat')} detected in {filename}",
            "description": (
                f"Automated incident from pipeline {pipeline_id}. "
                f"{len(rules)} threat signatures detected with severity {analysis.get('severity')}. "
                f"Source file stored at {s3_key}."
            ),
            "severity": analysis.get("severity", "HIGH"),
            "status": "open",
            "created_at": now,
            "updated_at": now,
            "assigned_to": None,
            "tags": ["automated", "pipeline", analysis.get("type", "unknown").lower().replace(" ", "-")],
            "log_entries": [f"Pipeline: {pipeline_id}", f"S3 Key: {s3_key}"],
            "matched_rules": [r.get("id", "") for r in rules],
            "resolution": None,
            "source": "pipeline",
            "pipeline_id": pipeline_id,
        }

        self.database.put_item(self.TABLE_INCIDENTS, incident)
        return incident

    # ──────────────────────────────────────────────────────────
    # Query Methods
    # ──────────────────────────────────────────────────────────

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline processing statistics."""
        # Enrich with database counts
        try:
            analysis_count = self.database.get_item_count(self.TABLE_ANALYSIS)
            incident_count = self.database.get_item_count(self.TABLE_INCIDENTS)
        except Exception:
            analysis_count = self._stats["total_logs_processed"]
            incident_count = 0

        return {
            "total_logs_processed": max(self._stats["total_logs_processed"], analysis_count),
            "total_threats_detected": self._stats["total_threats_detected"],
            "total_alerts_sent": self._stats["total_alerts_sent"],
            "total_incidents": incident_count,
            "pipeline_start_time": self._stats["pipeline_start_time"],
            "cloud_provider": self.config.provider,
            "services": {
                "storage": "S3" if self.config.provider == "aws" else "Local Filesystem",
                "database": "DynamoDB" if self.config.provider == "aws" else "SQLite",
                "notifications": "SNS" if self.config.provider == "aws" else "Local Console",
                "log_source": "CloudWatch" if self.config.provider == "aws" else "Local Files",
            },
        }

    def get_analysis_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent analysis history from DynamoDB."""
        return self.database.query(self.TABLE_ANALYSIS, limit=limit)

    def get_stored_logs(self, prefix: str = "") -> List[Dict[str, Any]]:
        """List stored log files from S3."""
        return self.storage.list_objects(prefix=prefix)

    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get alert history from SNS."""
        return self.notifications.get_alert_history(limit=limit)

    def get_log_sources(self) -> List[Dict[str, Any]]:
        """List available CloudWatch log groups."""
        return self.log_source.list_log_groups()

    def get_cloud_status(self) -> Dict[str, Any]:
        """Get cloud service health and configuration status."""
        status = {
            "provider": self.config.provider,
            "region": self.config.aws_region if self.config.provider == "aws" else "local",
            "services": {},
        }

        # Check each service
        try:
            self.storage.list_objects(prefix="__healthcheck__")
            status["services"]["storage"] = {
                "name": "S3" if self.config.provider == "aws" else "Local Filesystem",
                "status": "healthy",
                "endpoint": self.config.s3_bucket if self.config.provider == "aws" else self.config.s3_local_path,
            }
        except Exception as e:
            status["services"]["storage"] = {"name": "S3", "status": "error", "error": str(e)}

        try:
            self.database.get_item_count(self.TABLE_ANALYSIS)
            status["services"]["database"] = {
                "name": "DynamoDB" if self.config.provider == "aws" else "SQLite",
                "status": "healthy",
                "tables": [self.TABLE_INCIDENTS, self.TABLE_ANALYSIS],
            }
        except Exception as e:
            status["services"]["database"] = {"name": "DynamoDB", "status": "error", "error": str(e)}

        try:
            self.notifications.get_alert_count()
            status["services"]["notifications"] = {
                "name": "SNS" if self.config.provider == "aws" else "Local Console",
                "status": "healthy",
                "total_alerts": self.notifications.get_alert_count(),
            }
        except Exception as e:
            status["services"]["notifications"] = {"name": "SNS", "status": "error", "error": str(e)}

        try:
            groups = self.log_source.list_log_groups()
            status["services"]["log_source"] = {
                "name": "CloudWatch" if self.config.provider == "aws" else "Local Files",
                "status": "healthy",
                "log_groups": len(groups),
            }
        except Exception as e:
            status["services"]["log_source"] = {"name": "CloudWatch", "status": "error", "error": str(e)}

        return status


# Global pipeline instance
pipeline = SecurityPipeline()
