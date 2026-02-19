# System Architecture Diagrams & Explanations

## 🏗️ 1. Overall System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACE LAYER                        │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐│
│  │                      STREAMLIT (Port 8501)                      ││
│  │                                                                ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐││
│  │  │  Patient UI  │  │  Nurse UI    │  │  System Monitor     │││
│  │  │              │  │              │  │                      │││
│  │  │ • Login      │  │ • Cases      │  │ • Health checks     │││
│  │  │ • Symptoms   │  │ • Approve    │  │ • Metrics           │││
│  │  │ • Results    │  │ • Reject     │  │ • Logs              │││
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘││
│  └──────────────────┬───────────────────────────────────────────────┘│
│                     │ HTTP Requests (JSON)                           │
└─────────────────────┼──────────────────────────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────────────────────────┐
│                       REST API LAYER (FastAPI)                        │
│                          Port: 8000                                   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  Endpoints:                                                     │ │
│  │  • POST /patient/interact       → Triage symptoms             │ │
│  │  • POST /appointment/authorize  → Generate JWT                │ │
│  │  • POST /appointment/schedule   → Book appointment            │ │
│  │  • POST /nurse/approve          → Approve case                │ │
│  │  • GET /nurse/pending-reviews   → List cases                  │ │
│  │  • GET /agent/status            → System health               │ │
│  │  • GET /health                  → Connectivity check          │ │
│  │                                                                 │ │
│  │  Features:                                                     │ │
│  │  • Pydantic validation          • CORS enabled               │ │
│  │  • Error handling               • Request logging             │ │
│  │  • OpenAPI/Swagger docs         • Dependency injection        │ │
│  └──────────┬──────────────────────────────────┬──────────────────┘ │
│             │                                  │                    │
│  ┌──────────▼──────────┐     ┌────────────────▼───────────────┐   │
│  │   Agent Processing  │     │     External Services          │   │
│  │                     │     │                                │   │
│  │ Medi-Triage Agent   │────►│ • Google LLM API              │   │
│  │ (5 Layers)          │     │ • Sentence-Transformers       │   │
│  └──────────┬──────────┘     └────────────────┬───────────────┘   │
│             │                                  │                    │
└─────────────┼──────────────────────────────────┼────────────────────┘
              │                                  │
    ┌─────────┼──────────────────┬──────────────┼───────────┐
    │         │                  │              │           │
    │    ┌────▼─────┐    ┌───────▼────┐   ┌────▼──┐   ┌───▼──┐
    │    │  Input   │    │  Dialog    │   │Reasoning  │Tool  │
    │    │  Layer   │    │   Layer    │   │  Layer   │Layer │
    │    │          │    │            │   │          │      │
    │    │Anonymize │    │Emergency   │   │RAG w/    │Auth  │
    │    │PII with  │    │detection   │   │Chroma    │JWT   │
    │    │Presidio  │    │Topic check │   │Protocols │      │
    │    │Store in  │    │            │   │LLM call  │      │
    │    │Redis     │    │            │   │          │      │
    │    └────┬─────┘    └───────┬────┘   └─────┬────┘ └────┬─┘
    │         │                  │              │            │
    │    ┌────▼──────────────────▼──────────────▼────────────▼──┐
    │    │                                                       │
    │    │         WORKFLOW LAYER (Nurse Review)               │
    │    │                                                       │
    │    │         ┌──────────────────────────────┐             │
    │    │         │ Critical Case? YES            │             │
    │    │         │ ├─ Create interrupt          │             │
    │    │         │ ├─ Notify nurse              │             │
    │    │         │ ├─ Store in SQLite           │             │
    │    │         │ └─ Wait for approval         │             │
    │    │         └──────────────────────────────┘             │
    │    └────┬──────────────────────────────────────────────────┘
    │         │
    └─────────┼────────────────────────────────────────────┐
              │                                            │
    ┌─────────▼────────┐  ┌──────────────┐  ┌────────────▼──┐
    │  REDIS CACHE     │  │  CHROMA DB   │  │  SQLITE DB    │
    │  (Port 6379)     │  │  (Vector     │  │  (Local File) │
    │                  │  │   Store)     │  │               │
    │ ┌──────────────┐ │  │              │  │ Tables:       │
    │ │ PII Mappings │ │  │ ┌──────────┐ │  │ • appointments│
    │ │ • Tokens     │ │  │ │ Clinical │ │  │ • workflow    │
    │ │ • Sessions   │ │  │ │ Protocols│ │  │ • interrupts  │
    │ │ • TTL: 1 hr  │ │  │ │ (vectors)│ │  │ • audit_logs  │
    │ └──────────────┘ │  │ │ Semantic │ │  │               │
    │                  │  │ │ Search   │ │  │               │
    └──────────────────┘  │ └──────────┘ │  └───────────────┘
                          │              │
                          │ SQLite       │ File-based
                          │ Backend      │
                          └──────────────┘
```

---

## 📊 2. Data Flow: Patient Input → Triage Decision

```
PATIENT INPUT
│
│ "I have severe chest pain and 
│  shortness of breath for 10 minutes"
│
▼────────────────────────────────────────────────────────────────────
│                  LAYER 1: INPUT LAYER
│
├─ Presidio Analysis
│  ├─ Detect PERSON: None found
│  ├─ Detect EMAIL: None found
│  ├─ Detect PHONE: None found
│  └─ Detect SSN: None found
│
├─ PII Mapping (No PII in this case)
│  └─ Redis: {} (empty, nothing to store)
│
└─ Output: Original text (no anonymization needed)
│           Text is passed to Layer 2
│
▼────────────────────────────────────────────────────────────────────
│                  LAYER 2: DIALOG LAYER
│
├─ Emergency Detection
│  ├─ Check keywords: "severe", "chest pain", "breathing"
│  └─ Result: EMERGENCY ✓
│
├─ Topic Validation
│  ├─ Is this medical? YES ✓
│  └─ Is this on-topic? YES ✓
│
├─ Set Alert Level
│  └─ CRITICAL (due to emergency keywords)
│
└─ Output: Alert Level = CRITICAL, Routing = EMERGENCY
│           Proceed to Layer 3
│
▼────────────────────────────────────────────────────────────────────
│                  LAYER 3: REASONING LAYER
│
├─ Convert to Vector Embedding
│  └─ [0.23, 0.45, 0.12, ..., 0.89] (384 dimensions)
│
├─ Search Chroma DB
│  ├─ Query: Find k=3 similar protocols
│  └─ Results:
│     1. Acute Coronary Syndrome (95% similarity)
│     2. Pulmonary Embolism (92% similarity)
│     3. Myocardial Infarction (89% similarity)
│
├─ Prepare Context for LLM
│  └─ "User input: {text}
│     Similar protocols: {1, 2, 3}
│     Previous context: {history}"
│
├─ Call Google LLM
│  ├─ Model: gemini-1.5-flash
│  ├─ Prompt: [Include protocols as context]
│  └─ Response: "This is a potential cardiac emergency.
│                The patient's symptoms match Acute Coronary Syndrome
│                and Pulmonary Embolism profiles.
│                URGENT: Patient should call 911 immediately."
│
├─ Faithfulness Check (Ragas)
│  └─ Score: 98% (high confidence in response)
│
└─ Output: Triage Category = Acute Coronary Syndrome
│           Faithfulness = 98%
│           Proceed to Layer 4
│
▼────────────────────────────────────────────────────────────────────
│                  LAYER 4: TOOL LAYER
│
├─ Authorization Check
│  ├─ Is JWT token provided? No (patient input, not appointment)
│  └─ Skip authorization for triage
│
└─ Output: Authorization passed
│           Proceed to Layer 5
│
▼────────────────────────────────────────────────────────────────────
│                  LAYER 5: WORKFLOW LAYER
│
├─ Check Alert Level
│  ├─ Alert Level = CRITICAL
│  └─ Is Critical? YES → Interrupt required ✓
│
├─ Create Nurse Interrupt
│  ├─ Interrupt ID: INT-xyz123
│  ├─ Patient ID: PATIENT-001
│  ├─ Timestamp: 2024-02-18 10:30:45
│  └─ Store in SQLite
│
├─ Notification
│  └─ Alert nursing staff immediately
│
└─ Output: Status = PENDING_NURSE_APPROVAL
│           Interrupt ID = INT-xyz123
│           Wait for nurse response
│
▼────────────────────────────────────────────────────────────────────

FINAL RESPONSE TO PATIENT:

{
  "interaction_id": "int-abc123",
  "alert_level": "CRITICAL",
  "routing_decision": "EMERGENCY",
  "triage_category": "Acute Coronary Syndrome",
  "pii_detected": 0,
  "final_response": "Your symptoms suggest a potential cardiac 
                     emergency. A nurse is reviewing your case now.
                     If symptoms worsen, CALL 911 IMMEDIATELY.",
  "pending_nurse_review": true,
  "interrupt_id": "INT-xyz123",
  "layers_processed": [
    "input_layer",
    "dialog_layer", 
    "reasoning_layer",
    "tool_layer",
    "workflow_layer"
  ]
}

▼────────────────────────────────────────────────────────────────────

NURSE REVIEW (Later):

Nurse sees interrupt on dashboard:
├─ Patient: PATIENT-001
├─ Alert: CRITICAL
├─ Original Input: "I have severe chest pain..."
├─ AI Assessment: "Potential ACS, call 911"
└─ Actions: [APPROVE] [REJECT] [Notes field]

Nurse clicks APPROVE with notes:
├─ Interrupt resolved
├─ Patient notified of approval
├─ Final response sent
└─ Case closed
```

---

## 🔐 3. PII Anonymization Flow (When PII is Present)

```
RAW INPUT (WITH PII):
│
│ "My name is Sarah Johnson.
│  I was born on August 15, 1985.
│  My SSN is 123-45-6789.
│  Call me at (555) 123-4567.
│  I have been experiencing migraines."
│
▼───────────────────────────────────────────
│      PRESIDIO ANALYSIS
│
├─ PERSON: "Sarah Johnson"
│  └─ Confidence: 0.98, Position: 11-24
│
├─ DATE: "August 15, 1985"
│  └─ Confidence: 0.92, Position: 48-63
│
├─ SSN: "123-45-6789"
│  └─ Confidence: 0.95, Position: 85-96
│
├─ PHONE_NUMBER: "(555) 123-4567"
│  └─ Confidence: 0.90, Position: 114-128
│
└─ [Filter by threshold 0.3] ✓ All pass
│
▼───────────────────────────────────────────
│      ANONYMIZATION
│
├─ Replace PERSON: <PERSON>
├─ Replace DATE: <DATE>
├─ Replace SSN: <SSN>
├─ Replace PHONE_NUMBER: <PHONE_NUMBER>
│
▼───────────────────────────────────────────

ANONYMIZED OUTPUT:
│
│ "My name is <PERSON>.
│  I was born on <DATE>.
│  My SSN is <SSN>.
│  Call me at <PHONE_NUMBER>.
│  I have been experiencing migraines."
│
▼───────────────────────────────────────────
│      REDIS STORAGE (TTL = 1 HOUR)
│
├─ Key: pii_mapping:session-001:PERSON_abc123
│  Value: "Sarah Johnson" (encrypted hash)
│  TTL: 3600 seconds
│
├─ Key: pii_mapping:session-001:DATE_def456
│  Value: "August 15, 1985" (encrypted hash)
│  TTL: 3600 seconds
│
├─ Key: pii_mapping:session-001:SSN_ghi789
│  Value: "123-45-6789" (encrypted hash)
│  TTL: 3600 seconds
│
└─ Key: pii_mapping:session-001:PHONE_NUMBER_jkl012
   Value: "(555) 123-4567" (encrypted hash)
   TTL: 3600 seconds
│
▼───────────────────────────────────────────

WHAT LLM SEES:
│
│ "My name is <PERSON>.
│  I was born on <DATE>.
│  My SSN is <SSN>.
│  Call me at <PHONE_NUMBER>.
│  I have been experiencing migraines."
│
│ ✓ No actual PII visible to LLM
│ ✓ Only clinical info is visible
│ ✓ Mappings will auto-delete in 1 hour
│
▼───────────────────────────────────────────

SESSION METADATA IN REDIS:
│
├─ Key: session:session-001
│  Value: {
│    "created_at": "2024-02-18T10:30:45Z",
│    "user_id": "PATIENT-001",
│    "entity_count": 4,
│    "entities": ["PERSON", "DATE", "SSN", "PHONE_NUMBER"]
│  }
│  TTL: 86400 seconds (24 hours)
│
▼───────────────────────────────────────────

DEANONYMIZATION (If authorized):
│
├─ At any point in session, can retrieve:
│  PERSON_abc123 → "Sarah Johnson"
│  DATE_def456 → "August 15, 1985"
│  SSN_ghi789 → "123-45-6789"
│  PHONE_NUMBER_jkl012 → "(555) 123-4567"
│
├─ Usage: Only when responding to patient
│  (Never sent to LLM)
│
└─ Access: Logged for audit trail
```

---

## 🗄️ 4. Database Schemas

### **SQLite: Workflow State**
```
appointments
├─ id (PRIMARY KEY)
├─ patient_id
├─ appointment_date
├─ appointment_type
├─ reason
├─ status
├─ confirmation_number
├─ created_at
└─ updated_at

workflow_state
├─ id (PRIMARY KEY)
├─ interaction_id
├─ user_id
├─ session_id
├─ status
├─ created_at
└─ updated_at

nurse_interrupts
├─ id (PRIMARY KEY)
├─ interrupt_id
├─ patient_id
├─ alert_level
├─ triage_category
├─ original_message
├─ ai_assessment
├─ nurse_decision (approve/reject)
├─ nurse_id
├─ created_at
└─ updated_at

audit_logs
├─ id (PRIMARY KEY)
├─ timestamp
├─ user_id
├─ action
├─ resource
├─ status
└─ details
```

### **Redis: Cache Keys**
```
pii_mapping:{session_id}:{token}
├─ Key: pii_mapping:sess-001:PERSON_abc
├─ Value: "encrypted_hash_of_original"
└─ TTL: 3600 seconds

session:{session_id}
├─ Key: session:sess-001
├─ Value: {json with metadata}
└─ TTL: 86400 seconds

jwt_token:{token}
├─ Key: jwt_token:eyJhbGc...
├─ Value: {claims}
└─ TTL: 3600 seconds
```

### **Chroma DB: Vector Store**
```
Clinical Protocols (Embeddings):

Document 1:
├─ Content: "Acute Coronary Syndrome protocol..."
├─ Embedding: [0.23, 0.45, 0.12, ...] (384 dims)
├─ Metadata: {
│  "protocol_id": "ACS-001",
│  "category": "Cardiology",
│  "severity": "Critical"
│}
└─ Semantic Index: [for fast search]

Document 2:
├─ Content: "Pulmonary Embolism protocol..."
├─ Embedding: [0.34, 0.56, 0.23, ...] (384 dims)
├─ Metadata: {
│  "protocol_id": "PE-002",
│  "category": "Pulmonology",
│  "severity": "Critical"
│}
└─ Semantic Index: [for fast search]

[... more protocols ...]

Query "chest pain breathing"
├─ Convert to embedding: [0.25, 0.42, 0.15, ...]
├─ Find k=3 nearest neighbors
└─ Return: [ACS-001, PE-002, MI-003]
```

---

## 🔗 5. JWT Authorization Flow (Confused Deputy Prevention)

```
SCENARIO 1: LEGITIMATE REQUEST
│
├─ Patient PAT-123 requests token
│  └─ POST /appointment/authorize
│     {
│       "patient_id": "PAT-123",
│       "user_id": "USER-001",
│       "expires_in": 3600
│     }
│
├─ Server generates JWT with claims
│  └─ Header: {alg: "HS256", typ: "JWT"}
│     Payload: {
│       "patient_id": "PAT-123",
│       "user_id": "USER-001",
│       "exp": 1234567890
│     }
│     Signature: HMAC256(payload, secret_key)
│
├─ Returns token to patient
│  └─ "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
│
├─ Patient uses token to schedule appointment
│  └─ POST /appointment/schedule
│     Header: Authorization: <JWT_TOKEN>
│     Body: {
│       "patient_id": "PAT-123",
│       "date": "2024-02-25T10:00:00",
│       ...
│     }
│
├─ Server verifies token
│  ├─ Decode JWT → Get claims
│  ├─ Check: claims.patient_id == request.patient_id
│  │  PAT-123 == PAT-123 ✓
│  └─ Proceed with appointment booking
│
└─ RESULT: ✓ SUCCESS


SCENARIO 2: CONFUSED DEPUTY ATTACK
│
├─ Attacker tries to steal token
│  ├─ Intercepts: Token for PAT-123
│  └─ Tries to use for: PAT-456
│
├─ POST /appointment/schedule
│  ├─ Header: Authorization: <PAT-123_TOKEN>
│  └─ Body: {
│       "patient_id": "PAT-456",
│       "date": "2024-02-25T10:00:00",
│       ...
│     }
│
├─ Server verifies token
│  ├─ Decode JWT → Get claims
│  ├─ Check: claims.patient_id == request.patient_id
│  │  PAT-123 != PAT-456 ✗ MISMATCH
│  └─ Reject request
│
└─ RESULT: ✗ REJECTED - Attack prevented
```

---

## ⚡ 6. Real-time Processing Timeline

```
T+0ms    Patient submits: "I have chest pain"
         │
T+10ms   ├─ Input Layer: Presidio analysis (no PII found)
         │
T+30ms   ├─ Dialog Layer: Emergency detection (CRITICAL)
         │
T+100ms  ├─ Reasoning Layer:
         │  ├─ Create embedding
         │  ├─ Chroma search (k=3)
         │  ├─ Call Google LLM
         │  └─ Faithfulness check
         │
T+1200ms ├─ Tool Layer: Authorization check (skip)
         │
T+1250ms ├─ Workflow Layer: Create nurse interrupt
         │  ├─ Store in SQLite
         │  └─ Alert nursing staff
         │
T+1300ms └─ Return response to patient
            {
              "alert_level": "CRITICAL",
              "routing_decision": "EMERGENCY",
              "final_response": "Call 911 immediately",
              "pending_nurse_review": true
            }

TOTAL TIME: ~1.3 seconds from input to response
```

---

## 📈 7. System Load Distribution

```
Typical Daily Load (100 patients):

Time    Input  Dialog  Reasoning  Tool  Workflow  Total
06:00   2      2       2          0     1         7
09:00   15     14      12         3     5         49
12:00   20     19      15         4     8         66     [PEAK]
15:00   12     11      10         2     4         39
18:00   8      7       6          1     2         24
21:00   3      3       2          0     1         9
00:00   1      1       1          0     0         3

Resource Usage:

Redis Cache:
├─ Peak: 100 sessions × 4 PII items = 400 keys
├─ Memory: ~400KB (small)
└─ TTL cleanup: Automatic

Chroma DB:
├─ Vectors: 500 protocols
├─ Queries/min: ~2 (during peak)
└─ Memory: ~50MB (all in memory)

SQLite DB:
├─ New records/day: ~100 (appointments, interrupts)
├─ File size: ~10MB (grows slowly)
└─ Queries: ~5 per triage (mostly reads)

Google LLM:
├─ Calls/day: ~100
├─ Avg tokens: ~500 input, ~150 output
└─ Cost: ~$0.0001 per call
```

---

This architecture is **production-ready** and can handle realistic healthcare loads! 🎉
