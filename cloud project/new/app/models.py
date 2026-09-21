from typing import List, Optional, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field, validator


class AnalyzeRequest(BaseModel):
    logs: str = Field(..., description="Log payload to analyze (supports any text format)")

    @validator("logs")
    def logs_must_not_be_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("logs must be a non-empty string")
        return value


class MatchedRule(BaseModel):
    id: Optional[str]
    type: Optional[str]
    severity: Optional[str]
    description: Optional[str]
    pattern: Optional[str]
    count: int


class AnalyzeResponse(BaseModel):
    status: str = Field(..., description="Analysis status: clean, threat_detected, or error")
    type: str = Field(..., description="Primary threat type or 'none'")
    severity: str = Field(..., description="Highest severity: LOW, MEDIUM, HIGH, or CRITICAL")
    matchedRules: List[MatchedRule] = Field(default_factory=list)
    topRuleId: Optional[str] = None
    totalMatches: Optional[int] = None
    error: Optional[str] = None


class Incident(BaseModel):
    id: str = Field(..., description="Unique incident identifier")
    title: str = Field(..., description="Incident title/summary")
    description: str = Field(..., description="Detailed incident description")
    severity: str = Field(..., description="Incident severity: LOW, MEDIUM, HIGH, CRITICAL")
    status: str = Field(..., description="Incident status: open, investigating, resolved, closed")
    created_at: str = Field(..., description="ISO 8601 timestamp when incident was created")
    updated_at: str = Field(..., description="ISO 8601 timestamp when incident was last updated")
    assigned_to: Optional[str] = Field(None, description="User assigned to handle the incident")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    log_entries: List[str] = Field(default_factory=list, description="Original log entries that triggered the incident")
    matched_rules: List[str] = Field(default_factory=list, description="Rule IDs that matched")
    resolution: Optional[str] = Field(None, description="Resolution notes when incident is closed")


class CreateIncidentRequest(BaseModel):
    title: str = Field(..., description="Incident title")
    description: str = Field(..., description="Incident description")
    severity: str = Field(..., description="Incident severity")
    tags: List[str] = Field(default_factory=list, description="Incident tags")
    log_entries: List[str] = Field(default_factory=list, description="Log entries")
    matched_rules: List[str] = Field(default_factory=list, description="Matched rule IDs")


class UpdateIncidentRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    tags: Optional[List[str]] = None
    resolution: Optional[str] = None


# ──────────────────────────────────────────────────────────
# Cloud Pipeline Models
# ──────────────────────────────────────────────────────────


class PipelineUploadResponse(BaseModel):
    """Response from the pipeline upload endpoint."""
    pipeline_id: str = Field(..., description="Unique pipeline execution ID")
    filename: str = Field(..., description="Uploaded file name")
    status: str = Field(..., description="Pipeline execution status: completed or error")
    started_at: str = Field(..., description="Pipeline start timestamp")
    completed_at: Optional[str] = Field(None, description="Pipeline completion timestamp")
    stages: Dict[str, Any] = Field(default_factory=dict, description="Per-stage execution results")
    error: Optional[str] = Field(None, description="Error message if pipeline failed")


class PipelineStats(BaseModel):
    """Pipeline processing statistics."""
    total_logs_processed: int = Field(0, description="Total log files processed through the pipeline")
    total_threats_detected: int = Field(0, description="Total threats detected across all analyses")
    total_alerts_sent: int = Field(0, description="Total SNS alerts published")
    total_incidents: int = Field(0, description="Total incidents in DynamoDB")
    pipeline_start_time: str = Field(..., description="When the pipeline was initialized")
    cloud_provider: str = Field(..., description="Active cloud provider: local or aws")
    services: Dict[str, str] = Field(default_factory=dict, description="Cloud service mapping")


class CloudServiceStatus(BaseModel):
    """Health status of a single cloud service."""
    name: str = Field(..., description="Service name (e.g., S3, DynamoDB, SNS)")
    status: str = Field(..., description="Service status: healthy or error")
    endpoint: Optional[str] = Field(None, description="Service endpoint or path")
    tables: Optional[List[str]] = Field(None, description="Database tables (DynamoDB)")
    total_alerts: Optional[int] = Field(None, description="Total alerts (SNS)")
    log_groups: Optional[int] = Field(None, description="Number of log groups (CloudWatch)")
    error: Optional[str] = Field(None, description="Error details if unhealthy")


class CloudStatus(BaseModel):
    """Overall cloud infrastructure status."""
    provider: str = Field(..., description="Active cloud provider: local or aws")
    region: str = Field(..., description="Cloud region or 'local'")
    services: Dict[str, CloudServiceStatus] = Field(
        default_factory=dict, description="Status of each cloud service"
    )


class IngestRequest(BaseModel):
    """Request to ingest logs from a CloudWatch log group."""
    log_group: str = Field(..., description="CloudWatch log group name to ingest from")


class IngestResponse(BaseModel):
    """Response from CloudWatch log ingestion."""
    ingest_id: str = Field(..., description="Unique ingestion ID")
    log_group: str = Field(..., description="Source log group")
    status: str = Field(..., description="Ingestion status")
    events_fetched: int = Field(0, description="Number of log events fetched")
    threats_found: int = Field(0, description="Number of threats detected")
    analysis_summary: Optional[Dict[str, Any]] = Field(None, description="Analysis results")
    error: Optional[str] = Field(None, description="Error if ingestion failed")


class AlertRecord(BaseModel):
    """A single alert from the notification history."""
    id: str = Field(..., description="Alert ID")
    subject: str = Field(..., description="Alert subject line")
    message: str = Field(..., description="Alert message body")
    severity: str = Field(..., description="Alert severity")
    timestamp: str = Field(..., description="When the alert was sent")
    status: str = Field(..., description="Delivery status")
    provider: str = Field(..., description="Notification provider used")


class LogGroupInfo(BaseModel):
    """Metadata about a CloudWatch log group."""
    name: str = Field(..., description="Log group name")
    arn: str = Field("", description="Log group ARN")
    log_file_count: Optional[int] = Field(None, description="Number of log files/streams")
    total_events: Optional[int] = Field(None, description="Total log events")
    total_size_bytes: Optional[int] = Field(None, description="Total storage size in bytes")
    last_event_time: Optional[str] = Field(None, description="Timestamp of most recent event")
    provider: str = Field("local", description="Provider type")
