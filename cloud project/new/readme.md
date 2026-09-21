# Enterprise Security Log Analysis Platform

A **cloud-native, event-driven** FastAPI platform for cybersecurity threat detection and incident management. Features a pluggable cloud service abstraction layer supporting both local development and AWS deployment.

**Core Features:**
- 🔍 Advanced threat detection (35+ regex patterns)
- ☁️ Cloud-native pipeline with S3, DynamoDB, SNS, CloudWatch abstractions
- ⚡ Event-driven processing: Upload → Store → Analyze → Alert
- 📋 Incident management with full lifecycle tracking
- 📊 Real-time dashboard with cloud service health monitoring
- 🔔 Automated alerting for HIGH/CRITICAL threats
- 🛡️ Format-agnostic log analysis (any text-based format)
- ☁️ Multi-cloud ready (AWS Lambda, Azure Functions, Docker)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Web UI / API Client                      │
├──────────┬──────────┬──────────────┬───────────────┬────────────┤
│ Analyze  │ Upload   │ CloudWatch   │  Dashboard    │ Incidents  │
│ Logs     │ Log File │ Ingest       │  Stats        │ Management │
└────┬─────┴────┬─────┴──────┬───────┴───────┬───────┴─────┬──────┘
     │          │            │               │             │
     ▼          ▼            ▼               ▼             ▼
┌────────────────────────────────────────────────────────────────┐
│                     FastAPI Application                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Security Processing Pipeline                 │  │
│  │  Upload → Store(S3) → Analyze → Store(DynamoDB) → Alert  │  │
│  └──────────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────────┤
│              Cloud Service Abstraction Layer                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ Storage  │ │ Database │ │  Alerts  │ │   Log Sources    │  │
│  │  (S3)    │ │(DynamoDB)│ │  (SNS)   │ │  (CloudWatch)    │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────────┬─────────┘  │
│       │             │            │                 │            │
│  ┌────┴─────────────┴────────────┴─────────────────┴────────┐  │
│  │  CLOUD_PROVIDER=local          CLOUD_PROVIDER=aws        │  │
│  │  ├─ Filesystem                 ├─ AWS S3                 │  │
│  │  ├─ SQLite                     ├─ AWS DynamoDB           │  │
│  │  ├─ Console/JSON log           ├─ AWS SNS                │  │
│  │  └─ Local files                └─ AWS CloudWatch         │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Local Development

```powershell
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Start server (local cloud mode — default)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Visit: http://localhost:8000

### Cloud Provider Configuration

Set `CLOUD_PROVIDER` environment variable to switch backends:

| Mode | Command | What It Uses |
|------|---------|-------------|
| **Local** (default) | `CLOUD_PROVIDER=local` | Filesystem, SQLite, Console |
| **AWS** | `CLOUD_PROVIDER=aws` | S3, DynamoDB, SNS, CloudWatch |

See `.env.example` for all configuration options.

---

## Web UI Tabs

| Tab | Description |
|-----|-------------|
| **🔍 Log Analysis** | Paste logs and detect threats in real-time |
| **☁️ Cloud Pipeline** | Upload files to S3, ingest from CloudWatch, view processing flow |
| **📊 Dashboard** | Pipeline stats, cloud service health, SNS alert history |
| **📋 Incidents** | Track and manage security incidents |

---

## API Endpoints

### Log Analysis (Original)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/analyze_logs` | Analyze log text for threats |

### Cloud Pipeline
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/pipeline/upload` | Upload log file → S3 → Analyze → DynamoDB → SNS |
| `GET` | `/pipeline/stats` | Get pipeline processing statistics |
| `GET` | `/pipeline/history` | Get analysis history from DynamoDB |
| `GET` | `/pipeline/stored-logs` | List stored log files in S3 |

### CloudWatch Integration
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/cloud/log-groups` | List available CloudWatch log groups |
| `POST` | `/cloud/ingest` | Ingest & analyze logs from a CloudWatch log group |
| `GET` | `/cloud/status` | Cloud infrastructure health check |

### Alerting
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/alerts` | Get SNS alert history |

### Incident Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/incidents` | List all incidents |
| `POST` | `/incidents` | Create new incident |
| `GET` | `/incidents/{id}` | Get incident by ID |
| `PUT` | `/incidents/{id}` | Update incident |
| `DELETE` | `/incidents/{id}` | Delete incident |

---

## Cloud Pipeline Flow

When a log file is uploaded or CloudWatch logs are ingested:

1. **S3 Storage** — File is stored in S3 (local: `data/s3_storage/`)
2. **Lambda Analysis** — Threat detection engine scans for 35+ attack patterns
3. **DynamoDB Store** — Results are stored in DynamoDB (local: `data/dynamodb.sqlite`)
4. **SNS Alert** — If threats detected, alert published to SNS (local: `data/sns_alerts.json`)
5. **Auto-Incident** — HIGH/CRITICAL threats auto-create incidents in DynamoDB

---

## Project Structure

```
.
├── app/
│   ├── cloud/                   # Cloud service abstraction layer
│   │   ├── config.py            # Environment-based configuration
│   │   ├── storage.py           # S3 abstraction (Local + AWS)
│   │   ├── database.py          # DynamoDB abstraction (SQLite + AWS)
│   │   ├── notifications.py     # SNS abstraction (Console + AWS)
│   │   └── log_source.py        # CloudWatch abstraction (Files + AWS)
│   ├── main.py                  # FastAPI app + all routes
│   ├── analyzer.py              # Threat detection logic
│   ├── pipeline.py              # Event-driven processing pipeline
│   ├── incident_service.py      # Incident management
│   ├── models.py                # Request/response schemas
│   └── rules_loader.py          # Rule caching
├── frontend/
│   ├── index.html               # Web UI (4 tabs)
│   ├── style.css                # Styling
│   └── app.js                   # Client logic
├── data/
│   ├── detection_rules.json     # Detection patterns
│   ├── incidents.json           # Legacy incident storage
│   ├── s3_storage/              # Local S3 emulation (auto-created)
│   ├── dynamodb.sqlite          # Local DynamoDB emulation (auto-created)
│   ├── sns_alerts.json          # Local SNS emulation (auto-created)
│   └── log_sources/             # Local CloudWatch emulation (auto-created)
├── aws_lambda/handler.py        # AWS Lambda adapter
├── azure_function/              # Azure Functions adapter
├── .env.example                 # Configuration template
├── Dockerfile                   # Container image
├── requirements.txt             # Python dependencies
└── README.md
```

---

## Threat Detection

Detects 35+ threat types:
- **SQL Injection** — Tautology, UNION, destructive queries, time-based
- **XSS** — Script tags, event handlers, javascript URIs
- **Command Injection** — OS command chaining, shell encoding
- **Brute Force** — Repeated auth failures
- **Privilege Escalation** — Admin/root access patterns
- **SSRF** — Internal metadata access
- **XXE** — XML External Entity attacks
- **Path Traversal** — Directory traversal, sensitive files
- **LDAP/NoSQL Injection** — Filter manipulation
- **Data Exfiltration** — Transfer tools, credential exposure
- **Log4Shell, SSTI, JWT Exposure** — And more

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLOUD_PROVIDER` | `local` | Cloud backend: `local` or `aws` |
| `AWS_REGION` | `us-east-1` | AWS region |
| `AWS_ACCESS_KEY_ID` | — | AWS access key (AWS mode only) |
| `AWS_SECRET_ACCESS_KEY` | — | AWS secret key (AWS mode only) |
| `S3_BUCKET` | `security-logs-bucket` | S3 bucket name |
| `DYNAMODB_TABLE_INCIDENTS` | `SecurityIncidents` | DynamoDB incidents table |
| `DYNAMODB_TABLE_ANALYSIS` | `AnalysisHistory` | DynamoDB analysis table |
| `SNS_TOPIC_ARN` | `arn:aws:sns:...` | SNS topic ARN |
| `CLOUDWATCH_LOG_GROUP` | `/security/application-logs` | Default CloudWatch log group |

---

## Deployment

### Docker

```bash
docker build -t log-analyzer .
docker run -p 8000:80 log-analyzer
```

### AWS Lambda

1. Build and push image to ECR
2. Create Lambda function with container image
3. Configure API Gateway trigger
4. Set `CLOUD_PROVIDER=aws` and AWS credentials
5. Uses Mangum adapter automatically

### Azure Functions

1. Build and push image to ACR
2. Create Function App with container
3. Configure HTTP trigger
4. Uses ASGI wrapper automatically

---

## License

This project is provided as-is for demonstration and production use.
