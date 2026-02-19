# Deployment & Getting Started Guide

## Prerequisites

- Python 3.10+
- Redis server (for PII caching)
- PostgreSQL (for state persistence)
- OpenAI API key or Anthropic API key

## Local Development Setup

### 1. Clone and Setup Environment

```bash
# Clone repository
git clone https://github.com/your-org/guardrials.git
cd guardrials

# Create virtual environment
python3.10 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Redis

Redis is required for PII token caching:

```bash
# macOS
brew install redis
brew services start redis

# Linux
sudo apt-get install redis-server
sudo systemctl start redis-server

# Verify Redis is running
redis-cli ping
# Output: PONG
```

### 3. Configure Environment

```bash
# Copy example environment
cp .env.example .env

# Edit with your credentials
nano .env
# or
code .env
```

Key configurations:

```env
# Required
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # Leave empty if no password

# Security
SECRET_KEY=your-super-secret-key-change-in-production

# EHR Integration
EHR_API_BASE_URL=https://your-ehr-system.com/api
EHR_API_KEY=your-ehr-key

# Ragas Faithfulness
RAGAS_FAITHFULNESS_THRESHOLD=0.95

# Environment
ENVIRONMENT=development
DEBUG=True
```

### 4. Initialize Database (Optional)

```bash
# For production, setup PostgreSQL
export DATABASE_URL=postgresql://user:password@localhost:5432/medi_triage_db

# Run migrations (if using SQLAlchemy)
# python -m alembic upgrade head
```

### 5. Verify Installation

```bash
# Test imports
python -c "from app.agent import get_agent; print('✅ Installation successful')"

# Run health check
python -c "from app.agent import get_agent; agent = get_agent(); print(agent.get_agent_status())"
```

## Running Examples

```bash
# Run all example scenarios
python examples.py

# Expected output:
# MEDI-TRIAGE AGENT: COMPREHENSIVE EXAMPLE SCENARIOS
# ===============================================================
# EXAMPLE 1: Emergency Detection
# ...
# ✅ ALL EXAMPLES COMPLETED SUCCESSFULLY
```

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/test_dialog_layer.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html

# Run only safety tests
pytest tests/ -m safety -v
```

Expected test results:
```
test_agent_integration.py::TestMediTriageAgent::test_agent_initialization PASSED
test_agent_integration.py::TestMediTriageAgent::test_process_emergency_interaction PASSED
test_agent_integration.py::TestMediTriageAgent::test_process_normal_interaction PASSED
...
======================== 50 passed in 2.34s ========================
```

## Using the Agent in Your Application

### Quick Integration Example

```python
from app.agent import get_agent
from config.settings import get_settings

# Initialize agent
agent = get_agent()

# Process patient input
result = agent.process_patient_interaction(
    raw_user_input="I have a sore throat and fever",
    user_id="PATIENT-001",
    auth_token=optional_jwt_token
)

# Access results
print(f"Layers processed: {result['layers_processed']}")
print(f"Alert level: {result['dialog_result']['alert_level']}")
print(f"Final response: {result['final_response']}")

# Handle nurse review (if interrupt created)
if "interrupt_created" in result:
    interrupt_id = result["interrupt_created"]["interrupt_id"]
    
    # Later, nurse approves:
    approval = agent.handle_nurse_approval(
        interrupt_id=interrupt_id,
        nurse_id="NURSE-001",
        action="approve",
        notes="Patient approved for routine appointment"
    )
```

### Flask/FastAPI Integration

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.agent import get_agent

app = FastAPI()
agent = get_agent()

class PatientInput(BaseModel):
    user_id: str
    message: str
    auth_token: Optional[str] = None

@app.post("/triage")
async def process_triage(request: PatientInput):
    try:
        result = agent.process_patient_interaction(
            raw_user_input=request.message,
            user_id=request.user_id,
            auth_token=request.auth_token
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pending-reviews")
async def get_pending_reviews():
    """Get pending nurse reviews"""
    return agent.get_pending_nurse_reviews()

@app.post("/approve-interrupt/{interrupt_id}")
async def approve_interrupt(interrupt_id: str, nurse_id: str, action: str):
    """Nurse approves or modifies generated advice"""
    return agent.handle_nurse_approval(
        interrupt_id=interrupt_id,
        nurse_id=nurse_id,
        action=action
    )
```

## Production Deployment

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Environment
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV DEBUG=False

# Run application
CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
# Build image
docker build -t medi-triage-agent:latest .

# Run container with Redis
docker run -d --name redis redis:latest
docker run -d \
  --name medi-triage \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e REDIS_HOST=redis \
  -p 8000:8000 \
  --link redis \
  medi-triage-agent:latest
```

### Kubernetes Deployment

Create `k8s-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: medi-triage-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: medi-triage
  template:
    metadata:
      labels:
        app: medi-triage
    spec:
      containers:
      - name: agent
        image: your-registry/medi-triage-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: medi-triage-secrets
              key: openai-key
        - name: REDIS_HOST
          value: redis-service
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

Deploy:

```bash
kubectl apply -f k8s-deployment.yaml
kubectl get pods -l app=medi-triage
```

## Monitoring & Logging

### Health Checks

```python
# Health check endpoint
from app.agent import get_agent

agent = get_agent()
health = agent.get_agent_status()

if health["status"] == "healthy" and health["redis_healthy"]:
    print("✅ Agent is healthy")
else:
    print("❌ Agent has issues")
```

### Logging

All operations are logged as JSON for easy parsing:

```bash
# View logs (if running in terminal)
tail -f app.log

# Parse JSON logs (using jq)
tail -f app.log | jq '.level, .message'

# Filter for warnings/errors
tail -f app.log | jq 'select(.level == "WARNING")'
```

Sample log output:

```json
{
  "timestamp": "2024-02-17T10:30:15Z",
  "level": "INFO",
  "logger": "medi_triage_agent",
  "message": "Patient interaction started",
  "module": "agent",
  "function": "process_patient_interaction",
  "line": 45,
  "extra_fields": {
    "interaction_id": "abc-123",
    "user_id": "USER-001"
  }
}
```

## Troubleshooting

### Redis Connection Issues

```bash
# Check if Redis is running
redis-cli ping

# If not running:
# macOS
brew services start redis

# Linux
sudo systemctl start redis-server

# Docker
docker run -d -p 6379:6379 redis:latest
```

### OpenAI API Issues

```python
# Test OpenAI connection
import openai
openai.api_key = "your-key"
openai.Model.list()  # Should return list of models
```

### Tests Failing

```bash
# Check test environment
pytest tests/test_input_layer.py -v --tb=short

# Common issues:
# 1. Redis not running: Start Redis service
# 2. Missing .env file: Copy .env.example to .env
# 3. API keys not set: Ensure API keys in .env
```

## Performance Optimization

### Caching

The system uses Redis for PII token caching (1 hour default TTL):

```python
# Customize cache TTL in input_layer.py
self.ttl = 7200  # 2 hours instead of 1
```

### Vector Store

ChromaDB is used for clinical protocol storage. Optimize:

```python
# Increase similarity search results
retrieved = protocol_store.search_protocols(query, k=5)  # Instead of k=3

# Persist vector store
vector_store.persist()  # Saves to disk after modifications
```

### LLM Configuration

```python
# Use faster models for lower latency
OPENAI_MODEL=gpt-3.5-turbo  # Faster than gpt-4

# Set timeout
LLM_TIMEOUT=30  # seconds
```

## Security Checklist

Before production deployment:

- [ ] Change `SECRET_KEY` in .env to a strong random string
- [ ] Enable HTTPS/TLS for all connections
- [ ] Setup database encryption at rest
- [ ] Configure Redis password authentication
- [ ] Setup VPN/private network for EHR integration
- [ ] Enable audit logging for all nurse actions
- [ ] Setup alerts for emergency detections
- [ ] Implement rate limiting on API endpoints
- [ ] Configure HIPAA-compliant backup strategy
- [ ] Setup compliance monitoring and reporting

## Compliance Verification

### HIPAA Compliance Checklist

```bash
# Verify no PII reaches LLM
python -c "
from app.input_layer import get_anonymizer
anon = get_anonymizer()
text = 'SSN 123-45-6789'
anonymized, mapping = anon.analyze_and_anonymize(text)
assert '123-45-6789' not in anonymized
print('✅ PII anonymization working')
"

# Verify emergency routing
python -c "
from app.dialog_layer import get_dialog_orchestrator
orch = get_dialog_orchestrator()
result = orch.process_user_input('chest pain', 'session-1')
assert '911' in result['bot_response'].upper()
print('✅ Emergency routing working')
"

# Verify authorization checks
python -c "
from app.tool_layer import AppointmentAuthorizer
auth = AppointmentAuthorizer()
token = auth.generate_token('PAT-A', 'USER-1')
from app.tool_layer import AppointmentRequest
from datetime import datetime, timedelta
req = AppointmentRequest(
    patient_id='PAT-B',
    date=datetime.utcnow() + timedelta(days=7),
    reason='test appointment'
)
authorized, _ = auth.authorize_appointment_request(token, req)
assert not authorized
print('✅ Confused deputy prevention working')
"
```

## Support

- **Documentation**: See [README.md](README.md)
- **Issues**: Open GitHub issue with error logs
- **Security Issues**: Email security@yourdomain.com
- **Healthcare Questions**: Consult compliance officer

## Next Steps

1. ✅ Setup local environment
2. ✅ Run examples to verify installation
3. ✅ Run tests to ensure functionality
4. ✅ Integrate with your EHR system
5. ✅ Configure for production
6. ✅ Setup monitoring and logging
7. ✅ Deploy to production
8. ✅ Setup compliance reporting

---

**Last Updated**: February 17, 2024  
**Version**: 0.1.0
