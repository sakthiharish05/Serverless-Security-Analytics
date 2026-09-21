import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.models import Incident, CreateIncidentRequest, UpdateIncidentRequest


class IncidentService:
    def __init__(self):
        self.data_file = Path(__file__).resolve().parent.parent / "data" / "incidents.json"
        self.data_file.parent.mkdir(exist_ok=True)
        if not self.data_file.exists():
            self.data_file.write_text("[]")

    def _load_incidents(self) -> List[dict]:
        """Load incidents from JSON file."""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_incidents(self, incidents: List[dict]) -> None:
        """Save incidents to JSON file."""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(incidents, f, indent=2, ensure_ascii=False)

    def get_all_incidents(self) -> List[Incident]:
        """Get all incidents."""
        data = self._load_incidents()
        return [Incident(**incident) for incident in data]

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Get a specific incident by ID."""
        data = self._load_incidents()
        for incident in data:
            if incident['id'] == incident_id:
                return Incident(**incident)
        return None

    def create_incident(self, request: CreateIncidentRequest) -> Incident:
        """Create a new incident."""
        now = datetime.utcnow().isoformat() + "Z"

        incident = Incident(
            id=f"INC-{uuid.uuid4().hex[:8].upper()}",
            title=request.title,
            description=request.description,
            severity=request.severity,
            status="open",
            created_at=now,
            updated_at=now,
            assigned_to=None,
            tags=request.tags,
            log_entries=request.log_entries,
            matched_rules=request.matched_rules,
            resolution=None
        )

        data = self._load_incidents()
        data.append(incident.dict())
        self._save_incidents(data)

        return incident

    def update_incident(self, incident_id: str, request: UpdateIncidentRequest) -> Optional[Incident]:
        """Update an existing incident."""
        data = self._load_incidents()
        for i, incident in enumerate(data):
            if incident['id'] == incident_id:
                update_data = request.dict(exclude_unset=True)
                update_data['updated_at'] = datetime.utcnow().isoformat() + "Z"
                data[i].update(update_data)
                self._save_incidents(data)
                return Incident(**data[i])
        return None

    def delete_incident(self, incident_id: str) -> bool:
        """Delete an incident."""
        data = self._load_incidents()
        for i, incident in enumerate(data):
            if incident['id'] == incident_id:
                data.pop(i)
                self._save_incidents(data)
                return True
        return False

    def get_incidents_by_status(self, status: str) -> List[Incident]:
        """Get incidents filtered by status."""
        data = self._load_incidents()
        filtered = [incident for incident in data if incident.get('status') == status]
        return [Incident(**incident) for incident in filtered]

    def get_incidents_by_severity(self, severity: str) -> List[Incident]:
        """Get incidents filtered by severity."""
        data = self._load_incidents()
        filtered = [incident for incident in data if incident.get('severity') == severity]
        return [Incident(**incident) for incident in filtered]


# Global instance
incident_service = IncidentService()