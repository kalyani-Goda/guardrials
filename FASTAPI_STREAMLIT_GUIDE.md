"""
Quick Start Guide: FastAPI + Streamlit Implementation
"""

# ============================================================
# ARCHITECTURE OVERVIEW
# ============================================================

## Why Chroma DB for RAG?
- **Vector Embeddings**: Converts clinical protocols to vectors
- **Semantic Search**: "chest pain" queries find cardiology protocols even if worded differently
- **Local Storage**: SQLite backend ensures HIPAA compliance (no cloud)
- **Fast Retrieval**: In-memory operations for real-time triage

## Why Redis?
- **Speed**: In-memory cache for PII-to-token mappings
- **Auto-Expiration**: TTL-based cleanup (1 hour for PII, 24 hours for sessions)
- **Session Management**: Tracks user sessions and interactions
- **HIPAA Compliance**: Temporary storage with automatic deletion

## Why SQLite (Not PostgreSQL)?
- **Development**: Single-file database, no setup
- **Persistence**: Stores appointments, workflow states, nurse reviews
- **Scalability**: Move to PostgreSQL for production multi-server deployments

# ============================================================
# SETUP & INSTALLATION
# ============================================================

## 1. Install Dependencies
```bash
pip install -r requirements.txt
```

## 2. Install Additional Packages for FastAPI/Streamlit
```bash
pip install fastapi uvicorn streamlit plotly pandas
```

## 3. Download Spacy Model (required for Presidio)
```bash
python -m spacy download en_core_web_sm
```

## 4. Set Environment Variables
Create a `.env` file:
```
# Google LLM
GOOGLE_API_KEY=your_api_key_here
GOOGLE_MODEL=gemini-1.5-flash

# Redis (local)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Database
DATABASE_URL=sqlite:///./medi_triage.db

# Vector Store
VECTOR_STORE_PATH=./data/vector_store
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# JWT Secret
SECRET_KEY=your-secret-key-change-in-production

# Environment
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO
```

# ============================================================
# RUNNING THE APPLICATION
# ============================================================

## Option 1: Run Both FastAPI & Streamlit

### Terminal 1: Start Redis (required)
```bash
redis-server
```

### Terminal 2: Start FastAPI Backend
```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

API will be available at: http://localhost:8000
API Documentation: http://localhost:8000/docs (interactive Swagger UI)

### Terminal 3: Start Streamlit Frontend
```bash
streamlit run streamlit_app.py
```

Streamlit will open at: http://localhost:8501

## Option 2: Run Only FastAPI (for testing)
```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Test with curl:
```bash
curl -X POST http://localhost:8000/api/v1/patient/interact \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "PATIENT-001",
    "message": "I have severe chest pain"
  }'
```

## Option 3: Run Only Streamlit (for testing)
```bash
streamlit run streamlit_app.py
```

# ============================================================
# API ENDPOINTS
# ============================================================

### Health Check
GET /health

### Patient Interaction
POST /api/v1/patient/interact
{
  "user_id": "PATIENT-001",
  "message": "I have severe chest pain",
  "auth_token": "optional_jwt_token",
  "session_id": "optional_session_id"
}

### Generate JWT Token
POST /api/v1/appointment/authorize
{
  "patient_id": "PAT-12345",
  "user_id": "USER-001",
  "expires_in": 3600
}

### Schedule Appointment
POST /api/v1/appointment/schedule
{
  "patient_id": "PAT-12345",
  "appointment_date": "2024-02-25T10:00:00",
  "appointment_type": "primary_care",
  "reason": "Follow-up consultation",
  "preferred_specialist": null
}

Headers: Authorization: {jwt_token}

### Nurse Approval
POST /api/v1/nurse/approve
{
  "interrupt_id": "INTERRUPT-xyz",
  "nurse_id": "NURSE-001",
  "action": "approve",
  "notes": "Approved by nurse"
}

### Get Pending Reviews
GET /api/v1/nurse/pending-reviews

### Agent Status
GET /api/v1/agent/status

# ============================================================
# STREAMLIT INTERFACE
# ============================================================

### Features:
1. **Patient Login**: Patient symptom submission and triage
2. **Nurse Dashboard**: Review and approve triage cases
3. **System Monitor**: Real-time system health status
4. **Appointment Scheduling**: Book appointments through UI

### User Roles:
- **Patient**: Submit symptoms, view triage results, schedule appointments
- **Nurse**: Review critical cases, approve/reject recommendations
- **Admin**: Monitor system health and metrics

# ============================================================
# TESTING THE SYSTEM
# ============================================================

### Test Case 1: Emergency Detection
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/patient/interact",
    json={
        "user_id": "PATIENT-001",
        "message": "I'm having severe chest pain and I can't catch my breath"
    }
)
print(response.json())
```

Expected: alert_level = "CRITICAL"

### Test Case 2: PII Anonymization
```python
response = requests.post(
    "http://localhost:8000/api/v1/patient/interact",
    json={
        "user_id": "PATIENT-002",
        "message": "My name is Sarah Johnson, SSN is 123-45-6789, call me at (555) 123-4567"
    }
)
print(f"PII Detected: {response.json()['pii_detected']}")
```

Expected: pii_detected = 3+ (name, SSN, phone)

### Test Case 3: Appointment Authorization
```python
# Get token
token_response = requests.post(
    "http://localhost:8000/api/v1/appointment/authorize",
    json={
        "patient_id": "PAT-12345",
        "user_id": "USER-001",
        "expires_in": 3600
    }
)
token = token_response.json()['token']

# Schedule appointment
appt_response = requests.post(
    "http://localhost:8000/api/v1/appointment/schedule",
    json={
        "patient_id": "PAT-12345",
        "appointment_date": "2024-02-25T10:00:00",
        "appointment_type": "primary_care",
        "reason": "Consultation"
    },
    headers={"Authorization": token}
)
print(appt_response.json())
```

Expected: success = True

# ============================================================
# DEPLOYMENT
# ============================================================

### Using Docker

#### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt
RUN python -m spacy download en_core_web_sm

COPY . .

EXPOSE 8000 8501 6379

CMD ["sh", "-c", "redis-server --daemonize yes && python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 & streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0"]
```

#### docker-compose.yml
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  fastapi:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - REDIS_HOST=redis
    depends_on:
      - redis

  streamlit:
    build: .
    ports:
      - "8501:8501"
    environment:
      - API_URL=http://fastapi:8000
    depends_on:
      - fastapi
```

# ============================================================
# MONITORING & LOGS
# ============================================================

### Check Agent Status
```bash
curl http://localhost:8000/api/v1/agent/status
```

### View Logs
```bash
tail -f logs/app.log
```

### Redis Health
```bash
redis-cli ping
```

# ============================================================
# TROUBLESHOOTING
# ============================================================

### Redis Connection Error
```bash
# Ensure Redis is running
redis-server
# Or check if port 6379 is in use
lsof -i :6379
```

### Spacy Model Not Found
```bash
python -m spacy download en_core_web_sm
```

### Google API Key Error
```bash
# Ensure GOOGLE_API_KEY is set in .env
echo $GOOGLE_API_KEY
```

### Streamlit Connection Error
```bash
# Ensure FastAPI is running on port 8000
curl http://localhost:8000/health
# Update api_url in .streamlit/secrets.toml
```

# ============================================================
# NEXT STEPS
# ============================================================

1. ✅ Install all dependencies
2. ✅ Set up environment variables
3. ✅ Start Redis server
4. ✅ Start FastAPI backend
5. ✅ Start Streamlit frontend
6. ✅ Test with provided examples
7. ✅ Deploy to production

For questions or issues, refer to:
- API Documentation: http://localhost:8000/docs
- Code Comments: See api/main.py and streamlit_app.py
- Examples: See examples.py
