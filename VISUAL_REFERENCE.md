# **Visual Architecture Reference**

## **System Architecture Diagram**

```
┌─────────────────────────────────────────────────────────────────────┐
│                      MEDI-TRIAGE SYSTEM                             │
└─────────────────────────────────────────────────────────────────────┘

                          Patient Input
                                ↓
        ┌───────────────────────┴───────────────────────┐
        │                                               │
        
        ⭐ LAYER 1: INPUT (HIPAA Firewall)
        ├─ Presidio: Detect PII
        ├─ Anonymize: Replace with tokens
        └─ Redis: Cache PII mapping
        
        ↓
        
        ⭐ LAYER 2: DIALOG (Safety Gates)
        ├─ Regex: Check for emergencies
        ├─ Topics: Validate allowed topics
        └─ Route: Decide next action
        
        ↓
        
        ⭐ LAYER 3: REASONING (Clinical)
        ├─ ChromaDB: Retrieve protocols
        ├─ Google Gemini: Generate advice ← CLOUD CALL
        └─ Ragas: Validate faithfulness
        
        ↓
        
        ⭐ LAYER 4: TOOLS (Scheduling)
        ├─ JWT: Authorize request
        ├─ SQLite: Check availability
        └─ Save: Book appointment
        
        ↓
        
        ⭐ LAYER 5: WORKFLOW (Human Loop)
        ├─ Interrupt: Flag for review
        ├─ SQLite: Store state
        └─ Approval: Nurse reviews & approves
        
        ↓
        
        Patient Response (with original PII restored)
```

---

## **Data Storage Map**

```
┌─────────────────────────────────────────────────────────┐
│              YOUR LOCAL MACHINE                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  📁 medi_triage.db (SQLite Database)                   │
│  ├─ triage_sessions (patient records)                  │
│  ├─ appointments (scheduled visits)                    │
│  └─ audit_logs (HIPAA compliance)                      │
│                                                          │
│  💾 Redis (In-Memory Cache)                            │
│  ├─ PII mappings (encrypted)                           │
│  └─ Session data (temporary)                           │
│                                                          │
│  📚 data/vector_store/ (ChromaDB)                      │
│  └─ Clinical protocols (embeddings)                    │
│                                                          │
│  🔒 .env (Secrets - DON'T COMMIT)                      │
│  └─ GOOGLE_API_KEY=your-secret-key                     │
│                                                          │
└─────────────────────────────────────────────────────────┘

                            ↑
                      ONLY THIS
                   talks to internet
                            ↓

                    ☁️ Google Gemini API
                    (Free: 60 req/min)
```

---

## **Request Flow Timeline**

```
TIME → 

Patient Input (Raw Text)
  │
  ├─→ [0ms]   Presidio detects PII
  │   └─→ Redis caches mapping
  │
  ├─→ [5ms]   Regex checks emergencies
  │   └─→ If emergency: route 911
  │   └─→ Else: continue
  │
  ├─→ [10ms]  ChromaDB retrieves protocols
  │
  ├─→ [100ms] Google API generates advice  ← INTERNET CALL (slow)
  │
  ├─→ [110ms] Ragas validates response
  │
  ├─→ [115ms] SQLite saves to database
  │
  ├─→ [120ms] Workflow creates interrupt
  │   └─→ Waits for nurse approval
  │
  └─→ [?]     Nurse approves via dashboard
              ↓
              Response sent to patient
              (PII restored from Redis)

TOTAL: 120ms + human review time
```

---

## **Request Example Flow**

```
SCENARIO: Patient: "I'm John Doe, feeling dizzy, SSN 123-45-6789"

STEP 1: INPUT LAYER
┌─────────────────────────────────────────┐
│ Raw: "I'm John Doe, feeling dizzy..."   │
│                                         │
│ Presidio detects:                       │
│   - PERSON: John Doe                    │
│   - SSN: 123-45-6789                    │
│                                         │
│ Anonymized: "I'm <PERSON>, dizzy..."   │
│                                         │
│ Redis Cache:                            │
│   PERSON → "John Doe" (encrypted)       │
│   SSN → "123-45-6789" (encrypted)       │
└─────────────────────────────────────────┘
                   ↓
STEP 2: DIALOG LAYER
┌─────────────────────────────────────────┐
│ Text: "I'm <PERSON>, feeling dizzy..."  │
│                                         │
│ Emergency check: NO                     │
│ Topic check: "symptoms" (approved)      │
│                                         │
│ Decision: PROCEED_TO_TRIAGE             │
└─────────────────────────────────────────┘
                   ↓
STEP 3: REASONING LAYER
┌─────────────────────────────────────────┐
│ Symptoms: dizzy                         │
│                                         │
│ ChromaDB search:                        │
│   "Dizziness Protocol" (0.89 match)     │
│   "Vertigo Management" (0.85 match)     │
│                                         │
│ Google Gemini generates:                │
│   "Dizziness can be caused by..."       │
│   "Recommend seeing doctor..."          │
│                                         │
│ Faithfulness: 0.96 ✓ (>0.95 threshold) │
└─────────────────────────────────────────┘
                   ↓
STEP 4: TOOL LAYER
┌─────────────────────────────────────────┐
│ Offer: Schedule appointment?            │
│ User: "Yes, tomorrow morning"           │
│                                         │
│ Available doctors checked: YES          │
│ Appointment created:                    │
│   - Time: Tomorrow 9:00 AM              │
│   - Doctor: Dr. Smith                   │
│   - Saved to SQLite                     │
└─────────────────────────────────────────┘
                   ↓
STEP 5: WORKFLOW LAYER
┌─────────────────────────────────────────┐
│ Interrupt created:                      │
│   Type: MEDICAL_ADVICE_REVIEW           │
│   Status: PENDING_NURSE_APPROVAL        │
│   Saved to SQLite                       │
│                                         │
│ Waiting for nurse review...             │
│                                         │
│ Nurse sees in dashboard:                │
│   - Patient symptoms                    │
│   - Generated advice                    │
│   - Faithfulness score                  │
│                                         │
│ Nurse: "Approved, advice looks good"    │
└─────────────────────────────────────────┘
                   ↓
FINAL RESPONSE
┌─────────────────────────────────────────┐
│ De-anonymized from Redis:               │
│ "Hello John Doe,                        │
│                                         │
│ Based on your dizziness, you should:    │
│ 1. Rest in a quiet room                 │
│ 2. Stay hydrated                        │
│ 3. See a doctor if it persists          │
│                                         │
│ Appointment confirmed:                  │
│ Tomorrow 9:00 AM with Dr. Smith"        │
│                                         │
│ All data saved to SQLite database       │
└─────────────────────────────────────────┘
```

---

## **Database Schema**

```sql
-- Table 1: Triage Sessions
CREATE TABLE triage_sessions (
    session_id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    symptoms VARCHAR,
    anonymized_symptoms VARCHAR,
    triage_category VARCHAR,          -- EMERGENCY, URGENT, NORMAL
    generated_advice VARCHAR,
    faithfulness_score FLOAT,
    human_approved BOOLEAN,
    nurse_notes VARCHAR,
    created_at DATETIME,
    updated_at DATETIME,
    metadata JSON
);

-- Table 2: Appointments
CREATE TABLE appointments (
    appointment_id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    specialist VARCHAR,
    appointment_date DATETIME,
    status VARCHAR,                   -- scheduled, confirmed, completed
    created_at DATETIME,
    metadata JSON
);

-- Table 3: Audit Logs (HIPAA)
CREATE TABLE audit_logs (
    log_id VARCHAR PRIMARY KEY,
    action VARCHAR,
    user_id VARCHAR,
    details JSON,
    timestamp DATETIME
);
```

---

## **Configuration Map**

```
.env (Your Secrets)
├─ GOOGLE_API_KEY=AIzaSyD_xxxxx          ← KEEP SECRET
├─ GOOGLE_MODEL=gemini-1.5-flash
├─ DATABASE_URL=sqlite:///./medi_triage.db
├─ REDIS_HOST=localhost
├─ REDIS_PORT=6379
├─ VECTOR_STORE_TYPE=chromadb
├─ VECTOR_STORE_PATH=./data/vector_store
├─ LOG_LEVEL=INFO
└─ DEBUG=True

config/settings.py reads from .env:
├─ Google API settings
├─ Database settings
├─ Redis settings
├─ Logging settings
└─ Presidio settings
```

---

## **Component Interaction Matrix**

```
             │ Input │ Dialog │ Reasoning │ Tool │ Workflow
─────────────┼───────┼────────┼───────────┼──────┼──────────
Input Layer  │   ✓   │    ✓   │     ✓     │  ✓   │    ✓
Dialog Layer │       │    ✓   │     ✓     │  ✓   │    ✓
Reasoning    │       │        │     ✓     │  ✓   │    ✓
Tool Layer   │       │        │           │  ✓   │    ✓
Workflow     │       │        │           │      │    ✓
─────────────┼───────┼────────┼───────────┼──────┼──────────
Google API   │       │        │     ✓     │      │
SQLite       │       │        │           │  ✓   │    ✓
Redis Cache  │   ✓   │        │           │      │
ChromaDB     │       │        │     ✓     │      │
```

---

## **Cost Breakdown Pie Chart**

```
BEFORE (Old Setup)
┌─────────────────────────────┐
│  💰 $70/month               │
├─────────────────────────────┤
│ OpenAI GPT-4:  $50 (60%)   │
│ PostgreSQL:    $30 (43%)   │
│ Google Cloud:  $10 (14%)   │
│ Other:         $(20) (-29%) │
│                             │
│ WAIT, that's more than 70!  │
│ (Overlapping costs)         │
└─────────────────────────────┘

AFTER (Your Setup)
┌─────────────────────────────┐
│  💰 $0/month                │
├─────────────────────────────┤
│ Google Gemini: FREE (60 req/min)
│ SQLite:        FREE (local)
│ Redis:         FREE (local)
│ ChromaDB:      FREE (local)
│                             │
│ 🎉 100% Savings!           │
└─────────────────────────────┘
```

---

## **Health Check Status**

```
✅ Google Gemini API         Ready (if API key set)
✅ SQLite Database           Ready (auto-created)
✅ Redis Cache               Ready (if running)
✅ ChromaDB Vector Store     Ready (auto-created)
✅ Presidio PII Detection    Ready (installed)
✅ Spacy Models              Ready (downloaded)
✅ JWT Authentication        Ready (no setup)
✅ Workflow Orchestration    Ready (local)

All systems GO! 🚀
```

---

## **Quick Reference Card**

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃        MEDI-TRIAGE QUICK REFERENCE              ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                 ┃
┃ Setup:                                          ┃
┃   1. cp .env.example .env                       ┃
┃   2. Add GOOGLE_API_KEY to .env                 ┃
┃   3. pip install -r requirements.txt            ┃
┃   4. redis-server (background)                  ┃
┃   5. python examples.py                         ┃
┃                                                 ┃
┃ Test Components:                                ┃
┃   redis-cli ping                    → PONG      ┃
┃   sqlite3 medi_triage.db ".tables"  → tables    ┃
┃   python examples.py                → results  ┃
┃   pytest tests/ -v                  → tests    ┃
┃                                                 ┃
┃ Cost:  $0/month                                 ┃
┃ Speed: <500ms per request                       ┃
┃ Data:  100% local (except LLM)                  ┃
┃                                                 ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

---

**Print this page as reference while setting up!** 📋
