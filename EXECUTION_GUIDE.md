# 📋 Execution Guide - Medi-Triage Healthcare Agent

**Version:** 1.0.0 | **Status:** Production Ready | **Last Updated:** February 19, 2026

---

## Table of Contents

1. [Pre-Installation Requirements](#pre-installation-requirements)
2. [Installation Steps](#installation-steps)
3. [Configuration](#configuration)
4. [Running the System](#running-the-system)
5. [Development Mode](#development-mode)
6. [Production Deployment](#production-deployment)
7. [Verification & Testing](#verification--testing)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance](#maintenance)

---

## Pre-Installation Requirements

### System Requirements

- **OS:** macOS, Linux, or Windows
- **Python:** 3.10.18 or higher
- **Memory:** Minimum 4GB RAM, recommended 8GB
- **Storage:** 2GB free space
- **Network:** Internet for Google Gemini API, Redis connectivity

### Required Software

```bash
# Check Python version
python --version
# Should be: Python 3.10.18 or higher

# Check if conda is installed
conda --version
# Should show conda version

# Check if Redis is available
redis-cli --version
# Should show redis version
```

### API Keys Required

1. **Google Gemini API Key**
   - Get from: https://makersuite.google.com/app/apikey
   - Format: `AIza...` (long string)
   - Purpose: LLM for clinical assessment

### Network Requirements

- Internet connection for Google Gemini API
- Redis server accessibility (local: 127.0.0.1:6379)
- No special firewall rules needed for local development

---

## Installation Steps

### Step 1: Clone Repository

```bash
# Navigate to your projects directory
cd /Users/kalyani/Desktop/Projects

# Repository should already exist at:
cd guardrials
pwd
# Output: /Users/kalyani/Desktop/Projects/guardrials
```

### Step 2: Create Conda Environment

```bash
# Create environment with Python 3.10.18
conda create -n grenv python=3.10.18 -y

# Activate environment
conda activate grenv

# Verify activation
python --version
# Should show: Python 3.10.18
```

### Step 3: Install Dependencies

```bash
# Navigate to project root
cd /Users/kalyani/Desktop/Projects/guardrials

# Install all Python packages
pip install -r requirements.txt

# Verify installation (should be quick, no errors)
python -c "import fastapi; import streamlit; print('✅ Dependencies installed')"
```

### Step 4: Configure Environment Variables

```bash
# Create .env file in project root
cat > .env << EOF
# Google Gemini API
GOOGLE_API_KEY=your_api_key_here

# Redis Configuration
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

# Database Configuration
DATABASE_URL=sqlite:///medi_triage.db

# Logging
LOG_LEVEL=INFO
EOF
```

### Step 5: Initialize Database

```bash
# Activate environment
conda activate grenv

# Initialize SQLite database
python -c "
from app.local_database import LocalDatabase
db = LocalDatabase()
print('✅ Database initialized successfully')
print('   Location: medi_triage.db')
"
```

### Step 6: Start Redis

```bash
# Terminal 1: Start Redis server
redis-server

# Verify Redis is running (in another terminal):
redis-cli ping
# Should respond with: PONG
```

---

## Configuration

### Environment Variables

**File:** `.env` (in project root)

```bash
# ============ REQUIRED ============

# Google Gemini API Key (get from https://makersuite.google.com/app/apikey)
GOOGLE_API_KEY=AIzaSy...your_key_here...

# Redis Configuration
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

# Database Configuration
DATABASE_URL=sqlite:///medi_triage.db

# ============ OPTIONAL ============

# Logging Level
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# API Configuration
API_HOST=127.0.0.1
API_PORT=8000

# Streamlit Configuration
STREAMLIT_PORT=8502
STREAMLIT_HOST=0.0.0.0
```

### Configuration Files

**File:** `config/settings.py`

```python
# Logging settings
LOGGING_LEVEL = "INFO"

# API settings
API_HOST = "127.0.0.1"
API_PORT = 8000

# Database settings
DATABASE_URL = "sqlite:///medi_triage.db"

# Redis settings
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379

# Vector store settings
VECTOR_STORE_PATH = "data/vector_store/"
```

---

## Running the System

### 5-Layer Setup (All-in-One)

```bash
# Terminal 1: Redis Server
redis-server

# Terminal 2: API Server
conda activate grenv
cd /Users/kalyani/Desktop/Projects/guardrials
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000

# Terminal 3: Streamlit UI
conda activate grenv
cd /Users/kalyani/Desktop/Projects/guardrials
streamlit run streamlit_app.py --logger.level=error

# Access:
# UI: http://localhost:8502
# API: http://127.0.0.1:8000
# API Docs: http://127.0.0.1:8000/docs
```

### Component Startup Order

```
1. Redis Server (FIRST)
   └─ Provides caching for PII data
   
2. API Server (SECOND)
   └─ Depends on Redis
   └─ Serves REST endpoints
   
3. Streamlit UI (THIRD)
   └─ Connects to API server
   └─ Provides user interface
```

### Verify All Components Running

```bash
# Terminal 4: Verification Script
python << 'EOF'
import requests
import subprocess
import time

def check_redis():
    try:
        from redis import Redis
        r = Redis(host='127.0.0.1', port=6379)
        r.ping()
        print("✅ Redis: Running")
        return True
    except:
        print("❌ Redis: Not running")
        return False

def check_api():
    try:
        response = requests.get('http://127.0.0.1:8000/health', timeout=5)
        if response.status_code == 200:
            print("✅ API Server: Running")
            return True
    except:
        print("❌ API Server: Not running")
        return False

def check_database():
    try:
        from app.local_database import LocalDatabase
        db = LocalDatabase()
        print("✅ Database: Initialized")
        return True
    except:
        print("❌ Database: Not initialized")
        return False

print("\n=== System Status ===\n")
check_redis()
check_api()
check_database()
print("\n✅ All systems ready for testing\n")
EOF
```

---

## Development Mode

### Hot Reload Development

```bash
# Terminal 1: Redis (in background)
redis-server &

# Terminal 2: API with auto-reload
conda activate grenv
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 3: Streamlit with auto-reload
conda activate grenv
streamlit run streamlit_app.py --logger.level=debug

# Changes to Python files will auto-reload
```

### Running Tests

```bash
# Run all tests
conda activate grenv
pytest tests/ -v

# Run specific test file
pytest tests/test_agent_integration.py -v

# Run with coverage
pytest tests/ -v --cov=app --cov=api

# Run with output
pytest tests/ -v --tb=short -s
```

### Debug Mode

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: API with debug logging
conda activate grenv
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from api.main import app
import uvicorn
uvicorn.run(app, host='127.0.0.1', port=8000)
"

# Terminal 3: Streamlit with debug
conda activate grenv
streamlit run streamlit_app.py --logger.level=debug --client.showErrorDetails=true
```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] All tests passing: `pytest tests/ -v`
- [ ] Database initialized: `python -c "from app.local_database import LocalDatabase; db = LocalDatabase()"`
- [ ] Redis configured and tested
- [ ] Environment variables set in `.env`
- [ ] API health check passing: `curl http://localhost:8000/health`
- [ ] UI loads correctly: Visit http://localhost:8502
- [ ] SSL/TLS certificates ready (for HTTPS)
- [ ] Database backups configured

### Production Setup (Linux/Ubuntu)

#### 1. System Setup

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y python3.10 python3-pip redis-server supervisor nginx

# Create app user
sudo useradd -m -s /bin/bash medi-triage
sudo su - medi-triage
```

#### 2. Application Setup

```bash
# Clone repository
cd /opt
sudo git clone <repo-url> medi-triage
sudo chown -R medi-triage:medi-triage medi-triage

# Setup environment
cd /opt/medi-triage
conda create -n grenv python=3.10.18
conda activate grenv
pip install -r requirements.txt
```

#### 3. Configuration

```bash
# Set environment variables
cat > /opt/medi-triage/.env << EOF
GOOGLE_API_KEY=your_key
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
DATABASE_URL=sqlite:///medi_triage.db
LOG_LEVEL=INFO
EOF

# Initialize database
cd /opt/medi-triage
python -c "from app.local_database import LocalDatabase; db = LocalDatabase()"
```

#### 4. Systemd Services

**File:** `/etc/systemd/system/medi-triage-api.service`

```ini
[Unit]
Description=Medi-Triage API Server
After=network.target redis-server.service

[Service]
Type=notify
User=medi-triage
WorkingDirectory=/opt/medi-triage
Environment="PATH=/home/medi-triage/miniconda3/envs/grenv/bin"
EnvironmentFile=/opt/medi-triage/.env
ExecStart=/home/medi-triage/miniconda3/envs/grenv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker api.main:app --bind 0.0.0.0:8000
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**File:** `/etc/systemd/system/medi-triage-ui.service`

```ini
[Unit]
Description=Medi-Triage Streamlit UI
After=network.target medi-triage-api.service

[Service]
Type=simple
User=medi-triage
WorkingDirectory=/opt/medi-triage
Environment="PATH=/home/medi-triage/miniconda3/envs/grenv/bin"
EnvironmentFile=/opt/medi-triage/.env
ExecStart=/home/medi-triage/miniconda3/envs/grenv/bin/streamlit run streamlit_app.py --server.port=8502 --server.address=0.0.0.0
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 5. Enable Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable medi-triage-api.service
sudo systemctl enable medi-triage-ui.service
sudo systemctl start medi-triage-api.service
sudo systemctl start medi-triage-ui.service

# Check status
sudo systemctl status medi-triage-api.service
sudo systemctl status medi-triage-ui.service
```

#### 6. Nginx Reverse Proxy

**File:** `/etc/nginx/sites-available/medi-triage`

```nginx
upstream api_backend {
    server 127.0.0.1:8000;
}

upstream streamlit_app {
    server 127.0.0.1:8502;
}

server {
    listen 80;
    server_name medi-triage.example.com;
    
    # API endpoints
    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # Streamlit UI
    location / {
        proxy_pass http://streamlit_app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/medi-triage /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Docker Deployment

```bash
# Build image
docker build -t medi-triage:1.0.0 .

# Run with docker-compose
docker-compose up -d

# Check logs
docker-compose logs -f api
docker-compose logs -f ui
```

---

## Verification & Testing

### Health Checks

```bash
# 1. API Health
curl http://127.0.0.1:8000/health
# Expected: {"status": "healthy", ...}

# 2. Agent Status
curl http://127.0.0.1:8000/api/v1/agent/status
# Expected: Agent initialized and running

# 3. Redis Ping
redis-cli ping
# Expected: PONG

# 4. Database Check
python -c "
from app.local_database import LocalDatabase
db = LocalDatabase()
print('✅ Database operational')
"
```

### End-to-End Test

```bash
# 1. Patient submits case
curl -X POST http://127.0.0.1:8000/api/v1/patient/interact \
  -H "Content-Type: application/json" \
  -d '{"user_id": "PAT-TEST-001", "message": "I have severe joint pain"}'

# Response should include: interrupt_id, status, assessment

# 2. Get pending reviews (as nurse)
curl http://127.0.0.1:8000/api/v1/nurse/pending-reviews

# Response should show the case

# 3. Approve case with notes
curl -X POST http://127.0.0.1:8000/api/v1/nurse/approve \
  -H "Content-Type: application/json" \
  -d '{
    "interrupt_id": "INT-xxxxx",
    "nurse_id": "NURSE-TEST",
    "action": "approve",
    "notes": "Approved. Please bring medical history."
  }'

# 4. Patient views history
curl http://127.0.0.1:8000/api/v1/patient/PAT-TEST-001/history

# Should show approved status with nurse notes

# 5. Patient books appointment
curl -X POST http://127.0.0.1:8000/api/v1/appointment/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "PAT-TEST-001",
    "appointment_date": "2026-02-26",
    "appointment_type": "Specialist",
    "reason": "Joint pain consultation"
  }'
```

### Running Test Suite

```bash
# Run all tests with summary
pytest tests/ -v --tb=short

# Run specific test file
pytest tests/test_agent_integration.py -v

# Generate coverage report
pytest tests/ --cov=app --cov=api --cov-report=html

# Run with detailed output
pytest tests/ -v -s
```

### Expected Test Results

```
tests/test_agent_integration.py::test_agent_initialization PASSED
tests/test_agent_integration.py::test_process_emergency_interaction PASSED
tests/test_agent_integration.py::test_process_normal_interaction PASSED
tests/test_agent_integration.py::test_process_off_topic_interaction PASSED
tests/test_agent_integration.py::test_pii_anonymization_in_workflow PASSED
tests/test_agent_integration.py::test_dialog_result_in_response PASSED
tests/test_agent_integration.py::test_reasoning_result_in_response PASSED
tests/test_agent_integration.py::test_workflow_state_creation PASSED
tests/test_agent_integration.py::test_interrupt_creation_for_review PASSED
tests/test_agent_integration.py::test_handle_nurse_approval PASSED
tests/test_agent_integration.py::test_handle_nurse_modification PASSED
tests/test_agent_integration.py::test_get_pending_reviews PASSED
tests/test_agent_integration.py::test_agent_status_report PASSED
tests/test_agent_integration.py::test_error_handling PASSED
tests/test_agent_integration.py::test_get_global_agent PASSED
tests/test_agent_integration.py::test_global_agent_all_layers_initialized PASSED

========================= 16 passed in 16.34s =========================
```

---

## Troubleshooting

### Issue: "Connection refused" when starting API

```bash
# Check if Redis is running
redis-cli ping

# If not running:
redis-server

# Check if port 8000 is available
lsof -i :8000

# If port in use, kill process:
kill -9 <PID>
```

### Issue: "Database locked" error

```bash
# Delete database and reinitialize
rm medi_triage.db

# Reinitialize
python -c "from app.local_database import LocalDatabase; db = LocalDatabase()"
```

### Issue: "GOOGLE_API_KEY not found" error

```bash
# Verify .env file exists
cat .env

# If not, create it:
echo "GOOGLE_API_KEY=your_key_here" > .env

# Set environment variable
export GOOGLE_API_KEY=your_key_here
```

### Issue: API responds but Streamlit shows connection error

```bash
# Check API health
curl http://127.0.0.1:8000/health

# Restart Streamlit
streamlit run streamlit_app.py --logger.level=error --client.showErrorDetails=true

# Check Streamlit logs for detailed errors
```

### Issue: Tests failing

```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Run tests with verbose output
pytest tests/ -v -s --tb=long
```

---

## Maintenance

### Regular Maintenance Tasks

#### Daily
- Monitor system logs
- Check API health: `curl http://localhost:8000/health`
- Verify no pending reviews overflow

#### Weekly
- Review database size: `du -sh medi_triage.db`
- Check Redis memory: `redis-cli info memory`
- Review error logs

#### Monthly
- Backup database: `cp medi_triage.db medi_triage.db.backup.$(date +%Y%m%d)`
- Update dependencies: `pip install -r requirements.txt --upgrade`
- Review test coverage: `pytest --cov`

### Database Maintenance

```bash
# Backup database
cp medi_triage.db medi_triage.db.backup

# Optimize database
python -c "
from app.local_database import LocalDatabase
db = LocalDatabase()
db.optimize()
"

# Check database integrity
sqlite3 medi_triage.db "PRAGMA integrity_check;"
```

### Log Management

```bash
# View API logs
tail -f logs/api.log

# View Streamlit logs
tail -f logs/streamlit.log

# Clear old logs
find logs/ -type f -mtime +30 -delete
```

### Performance Monitoring

```bash
# Monitor system resources
watch -n 1 "ps aux | grep -E 'uvicorn|streamlit|redis'"

# Check database query performance
python -c "
from app.local_database import LocalDatabase
db = LocalDatabase()
import time
start = time.time()
cases = db.get_sessions_by_user('PAT-001')
print(f'Query time: {time.time() - start:.3f}s')
print(f'Cases retrieved: {len(cases)}')
"
```

---

## Summary

### Quick Reference

| Task | Command |
|------|---------|
| **Setup Environment** | `conda create -n grenv python=3.10.18` |
| **Install Dependencies** | `pip install -r requirements.txt` |
| **Initialize Database** | `python -c "from app.local_database import LocalDatabase; db = LocalDatabase()"` |
| **Start Redis** | `redis-server` |
| **Start API** | `python -m uvicorn api.main:app --host 127.0.0.1 --port 8000` |
| **Start UI** | `streamlit run streamlit_app.py` |
| **Run Tests** | `pytest tests/ -v` |
| **Check Health** | `curl http://127.0.0.1:8000/health` |
| **View API Docs** | Visit http://127.0.0.1:8000/docs |
| **Access UI** | Visit http://localhost:8502 |

### Key Files

- **API Server:** `api/main.py`
- **UI Application:** `streamlit_app.py`
- **Configuration:** `config/settings.py`, `.env`
- **Database:** `app/local_database.py`, `medi_triage.db`
- **Tests:** `tests/test_agent_integration.py`

### Support

For detailed architecture information, see [ARCHITECTURE_GUIDE.md](ARCHITECTURE_GUIDE.md)
For test implementation details, see [TEST_IMPLEMENTATION.md](TEST_IMPLEMENTATION.md)

---

**Status:** ✅ **PRODUCTION READY**

System is ready for deployment!
