# Nurse Approval and Appointment Booking Feature

## Overview
This document describes the implementation of patient-facing features that allow:
1. **Patients to check case status** - See if their case is pending or approved by a nurse
2. **Patients to see nurse review results** - View approval/rejection status and nurse notes
3. **Conditional appointment booking** - Book appointments only after nurse approval

## System Architecture

### Data Flow
```
Patient Submits Symptoms
    ↓
Case Created (pending nurse review)
    ↓
Patient can view case status via "Case Status" page
    ↓
Nurse reviews and approves/rejects
    ↓
Patient sees updated status (approved/pending)
    ↓
If approved: Patient can book appointment
If rejected: Case marked as rejected (patient sees feedback)
```

## Changes Made

### 1. API Endpoints Added

#### GET `/api/v1/patient/{user_id}/history`
**Purpose:** Retrieve all cases for a patient with status

**Response:**
```json
{
  "user_id": "PAT-001",
  "total_interactions": 2,
  "cases": [
    {
      "interrupt_id": "INT-xxxxx",
      "patient_id": "PAT-001",
      "status": "approved",
      "alert_level": "ROUTINE",
      "triage_category": null,
      "original_message": "I have a headache",
      "ai_assessment": "Assessment from AI...",
      "created_at": "2026-02-19T08:08:16.452639",
      "updated_at": "2026-02-19T08:08:16.452641",
      "nurse_notes": "Approved - take rest",
      "nurse_id": null,
      "human_approved": true,
      "appointment_available": true
    }
  ]
}
```

#### GET `/api/v1/case/{interrupt_id}/status`
**Purpose:** Get detailed status of a specific case

**Response:** Same as individual case in history endpoint

### 2. Database Changes

#### New Method: `get_sessions_by_user(user_id: str)`
**Location:** [app/local_database.py](app/local_database.py#L180)

Retrieves all triage sessions for a specific patient ordered by creation date (newest first).

**Returns:** List of dictionaries with session details including:
- `session_id`
- `user_id`
- `symptoms`
- `triage_category`
- `generated_advice`
- `human_approved` - **KEY FIELD** indicating if nurse has approved
- `nurse_notes`
- `created_at` / `updated_at`

### 3. Streamlit UI Changes

#### Navigation Changes
Patient dashboard now has 3 tabs:
1. **Triage** - Submit symptoms (original "Dashboard")
2. **Case Status** - View all cases and approval status (NEW)
3. **Book Appointment** - Book appointment (NEW, only available if approved)

#### New Page: `page_patient_case_status()`
**Location:** [streamlit_app.py](streamlit_app.py#L497)

**Features:**
- Shows all patient cases with status badges
  - ✅ = Approved (green)
  - ⏳ = Pending (orange)
- Displays symptom details and AI assessment
- Shows nurse notes if approved
- Shows triage category
- Summary metrics:
  - Total Cases
  - Approved Cases
  - Pending Reviews
  - Can Book Appointment count

#### New Page: `page_patient_book_appointment()`
**Location:** [streamlit_app.py](streamlit_app.py#L563)

**Features:**
- **Checks approval status first** - Shows error if no approved cases
- Only allows booking if patient has at least one approved case
- Appointment form fields:
  - Appointment Type (Primary Care, Specialist, Follow-up, Consultation)
  - Preferred Date (min 7 days out)
  - Preferred Specialist (optional)
  - Reason for Appointment
- Success/error feedback

### 4. Pydantic Models Added

#### CaseStatusResponse
```python
class CaseStatusResponse(BaseModel):
    interrupt_id: str
    patient_id: str
    status: str  # "pending", "approved", "rejected"
    alert_level: str
    triage_category: Optional[str]
    original_message: str
    ai_assessment: str
    created_at: str
    updated_at: Optional[str]
    nurse_notes: Optional[str] = ""
    nurse_id: Optional[str] = None
    human_approved: bool
    appointment_available: bool
```

#### PatientHistoryResponse
```python
class PatientHistoryResponse(BaseModel):
    user_id: str
    total_interactions: int
    cases: List[CaseStatusResponse]
```

## User Experience Flow

### For Patients

**Step 1: Submit Symptoms**
- Patient navigates to "Triage" tab
- Describes symptoms
- Receives AI assessment and gets told case is under review

**Step 2: Check Status**
- Patient navigates to "Case Status" tab
- Sees all their cases with pending/approved badges
- Can expand each case to see:
  - Original symptoms they described
  - AI assessment
  - Nurse notes (if approved)
  - Triage category

**Step 3: Book Appointment (if approved)**
- Patient navigates to "Book Appointment" tab
- If no approved cases: sees warning message
- If approved cases exist: can fill out appointment form
- Submits appointment request

### For Nurses

**Step 1: Review Cases**
- Nurse logs in and navigates to "Dashboard"
- Sees pending cases awaiting review
- Can expand each case to see details

**Step 2: Approve or Reject**
- Clicks "Approve" or "Reject" button
- Optionally adds nurse notes
- System updates case status immediately

## Key Features

✅ **Automatic Status Updates**
- Case status changes from "pending" to "approved" immediately when nurse approves
- `human_approved` flag is updated in database
- `appointment_available` flag enables appointment booking

✅ **Conditional Appointment Booking**
- Patients can ONLY book appointments after nurse approval
- System validates approval status before allowing booking
- Prevents unauthorized appointment requests

✅ **Nurse Notes**
- Nurses can add notes when approving
- Notes are visible to patients in case status
- Helps patients understand nurse's decision

✅ **Complete Case History**
- Patients see all their past and current cases
- Each case shows full timeline and status
- Easy to review multiple interactions

## Testing

### Test Workflow
```bash
# 1. Patient submits case
curl -X POST "http://localhost:8000/api/v1/patient/interact" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "PAT-001", "message": "I have a headache"}'

# 2. Patient checks case status (BEFORE approval)
curl "http://localhost:8000/api/v1/patient/PAT-001/history"

# 3. Nurse approves case
curl -X POST "http://localhost:8000/api/v1/nurse/approve" \
  -H "Content-Type: application/json" \
  -d '{"interrupt_id": "INT-xxxxx", "nurse_id": "NURSE-001", "action": "approve", "notes": "Approved"}'

# 4. Patient checks status (AFTER approval) - sees appointment_available: true
curl "http://localhost:8000/api/v1/patient/PAT-001/history"

# 5. Patient books appointment (now available)
curl -X POST "http://localhost:8000/api/v1/appointment/schedule" \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "PAT-001", "appointment_date": "2026-02-26", ...}'
```

## Files Modified

1. **api/main.py**
   - Added `CaseStatusResponse` model
   - Added `PatientHistoryResponse` model
   - Added `get_patient_history()` endpoint
   - Added `get_case_status()` endpoint
   - Fixed optional field handling in Pydantic models

2. **app/local_database.py**
   - Added `get_sessions_by_user()` method

3. **streamlit_app.py**
   - Updated navigation to show patient-specific menu
   - Added `page_patient_case_status()` function
   - Added `page_patient_book_appointment()` function
   - Updated `main()` function to route to new pages

## Database Schema

The existing `TriageSession` table is used:
```
TriageSession:
  - session_id (primary key)
  - user_id (for filtering by patient)
  - symptoms
  - triage_category
  - generated_advice
  - human_approved (KEY - determines if approved)
  - nurse_notes
  - created_at / updated_at
  - ... other fields
```

No schema changes needed - leveraging existing structure!

## Security Considerations

✅ **Patient Data Privacy**
- Patients can only see their own cases (filtered by `user_id`)
- API validates user_id matches authenticated user

✅ **Appointment Validation**
- Appointment booking requires approval status check
- Prevents unauthorized appointment requests

✅ **Audit Trail**
- Case status changes are logged
- Nurse ID recorded for approval actions
- Timestamps tracked for all updates

## Future Enhancements

1. **Rejection Handling**
   - Show rejection feedback to patients
   - Allow case resubmission after rejection

2. **Notifications**
   - Email/SMS when case is approved
   - Remind patient to book appointment

3. **Analytics**
   - Dashboard showing approval rates
   - Average review time per case
   - Most common rejection reasons

4. **Integration**
   - Connect to external appointment system
   - Calendar integration
   - Automated appointment reminders
