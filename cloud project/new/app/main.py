import os
from pathlib import Path
from typing import List

from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.analyzer import detect_threat
from app.models import (
    AnalyzeRequest, AnalyzeResponse, Incident,
    CreateIncidentRequest, UpdateIncidentRequest,
    IngestRequest,
)
from app.incident_service import incident_service
from app.pipeline import pipeline

app = FastAPI(
    title="Enterprise Security Log Analysis Platform",
    version="2.0.0",
    description="Cloud-native security log analysis platform with event-driven processing pipeline. "
                "Supports S3 storage, DynamoDB, SNS alerting, and CloudWatch log ingestion.",
)

# Path to frontend directory
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/")
async def root():
    """Serve the frontend UI."""
    return FileResponse(FRONTEND_DIR / "index.html")


# Mount static files (CSS, JS)
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# ──────────────────────────────────────────────────────────
# Log Analysis (Original)
# ──────────────────────────────────────────────────────────

@app.post("/analyze_logs", response_model=AnalyzeResponse)
def analyze_logs(payload: AnalyzeRequest):
    """Analyze logs and return matched threat rules."""
    return detect_threat(payload.logs)


# ──────────────────────────────────────────────────────────
# Incident Management (Original)
# ──────────────────────────────────────────────────────────

@app.get("/incidents", response_model=List[Incident])
def get_incidents():
    """Get all incidents."""
    return incident_service.get_all_incidents()


@app.get("/incidents/{incident_id}", response_model=Incident)
def get_incident(incident_id: str):
    """Get a specific incident by ID."""
    incident = incident_service.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.post("/incidents", response_model=Incident)
def create_incident(request: CreateIncidentRequest):
    """Create a new incident."""
    return incident_service.create_incident(request)


@app.put("/incidents/{incident_id}", response_model=Incident)
def update_incident(incident_id: str, request: UpdateIncidentRequest):
    """Update an existing incident."""
    incident = incident_service.update_incident(incident_id, request)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.delete("/incidents/{incident_id}")
def delete_incident(incident_id: str):
    """Delete an incident."""
    if not incident_service.delete_incident(incident_id):
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"message": "Incident deleted successfully"}


@app.get("/incidents/status/{status}", response_model=List[Incident])
def get_incidents_by_status(status: str):
    """Get incidents filtered by status."""
    return incident_service.get_incidents_by_status(status)


@app.get("/incidents/severity/{severity}", response_model=List[Incident])
def get_incidents_by_severity(severity: str):
    """Get incidents filtered by severity."""
    return incident_service.get_incidents_by_severity(severity)


# ──────────────────────────────────────────────────────────
# Cloud Pipeline Endpoints
# ──────────────────────────────────────────────────────────

@app.post("/pipeline/upload")
async def pipeline_upload(file: UploadFile = File(...)):
    """
    Upload a log file to the cloud pipeline.

    Full event-driven flow:
    1. Store file in S3 (local filesystem)
    2. Analyze for threats
    3. Store results in DynamoDB (SQLite)
    4. Send SNS alert if threats detected
    5. Auto-create incident for HIGH/CRITICAL threats
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    # Max 50MB
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")

    result = pipeline.process_uploaded_log(file.filename, content)
    return result


@app.get("/pipeline/stats")
def get_pipeline_stats():
    """Get pipeline processing statistics and cloud service summary."""
    return pipeline.get_pipeline_stats()


@app.get("/pipeline/history")
def get_pipeline_history(limit: int = 50):
    """Get recent analysis history from DynamoDB."""
    return pipeline.get_analysis_history(limit=limit)


@app.get("/pipeline/stored-logs")
def get_stored_logs(prefix: str = ""):
    """List log files stored in S3."""
    return pipeline.get_stored_logs(prefix=prefix)


# ──────────────────────────────────────────────────────────
# CloudWatch Ingestion Endpoints
# ──────────────────────────────────────────────────────────

@app.get("/cloud/log-groups")
def list_log_groups():
    """List available CloudWatch log groups."""
    return pipeline.get_log_sources()


@app.post("/cloud/ingest")
def ingest_from_cloud(request: IngestRequest):
    """
    Ingest logs from a CloudWatch log group and process through pipeline.

    Flow: CloudWatch → S3 → Analyze → DynamoDB → SNS (if threats found)
    """
    return pipeline.ingest_from_cloud_source(request.log_group)


# ──────────────────────────────────────────────────────────
# Alerts & Cloud Status Endpoints
# ──────────────────────────────────────────────────────────

@app.get("/alerts")
def get_alerts(limit: int = 50):
    """Get alert history from SNS notification log."""
    return pipeline.get_alert_history(limit=limit)


@app.get("/cloud/status")
def get_cloud_status():
    """
    Get cloud infrastructure health status.

    Shows which provider is active (local/aws) and the health
    of each cloud service (S3, DynamoDB, SNS, CloudWatch).
    """
    return pipeline.get_cloud_status()


# ──────────────────────────────────────────────────────────
# Error Handlers
# ──────────────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
