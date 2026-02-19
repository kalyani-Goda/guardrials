# Patient Case Status Page - Visual Guide

## 📊 Dashboard Summary

When patient opens "Case Status" tab, they see:

```
╔══════════════════════════════════════════════════════════════════════╗
║                         📋 CASE STATUS                              ║
║                  Patient ID: PAT-TEST-NOTES                         ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  ┌─────────────────┬──────────────┬──────────────┬──────────────┐  ║
║  │  Total Cases    │ Approved     │ Pending      │  Can Book    │  ║
║  │       2         │      1       │      1       │  Appt: 1     │  ║
║  └─────────────────┴──────────────┴──────────────┴──────────────┘  ║
║                                                                      ║
╠════════════════════════ RECENT CASES ═════════════════════════════╣
║                                                                      ║
║ ┌────────────────────────────────────────────────────────────────┐  ║
║ │ Case 1: b381fbca-0cc5-4f47-909e-391d380763c8                  │  ║
║ │ Created: 2026-02-19                                            │  ║
║ ├────────────────────────────────────────────────────────────────┤  ║
║ │ Status: ✅ APPROVED          |  Alert: ROUTINE        │ ✅ OK │  ║
║ ├────────────────────────────────────────────────────────────────┤  ║
║ │ ▼ 📝 Your Symptoms                                            │  ║
║ │   "I have severe joint pain and stiffness, especially in my    │  ║
║ │    knees when I wake up"                                       │  ║
║ │                                                                 │  ║
║ │ ▼ 💬 AI Assessment                                            │  ║
║ │   "The patient's symptoms suggest possible osteoarthritis or   │  ║
║ │    rheumatoid arthritis. Recommend specialist evaluation..."   │  ║
║ │                                                                 │  ║
║ │ ▼ 👨‍⚕️ Nurse Approval Notes  ✅ APPROVED                        │  ║
║ │   ┌──────────────────────────────────────────────────────────┐ │  ║
║ │   │ Approved for specialist consultation.                    │ │  ║
║ │   │                                                          │ │  ║
║ │   │ Please bring the following documents to your             │ │  ║
║ │   │ appointment:                                             │ │  ║
║ │   │                                                          │ │  ║
║ │   │ 1) Medical history records                               │ │  ║
║ │   │ 2) Latest blood work results                             │ │  ║
║ │   │ 3) Insurance card                                        │ │  ║
║ │   │ 4) Photo ID                                              │ │  ║
║ │   │                                                          │ │  ║
║ │   │ Appointment scheduled with orthopedic specialist.        │ │  ║
║ │   └──────────────────────────────────────────────────────────┘ │  ║
║ │                                                                 │  ║
║ │ Triage Category: ORTHOPEDIC_ISSUE                             │  ║
║ └────────────────────────────────────────────────────────────────┘  ║
║                                                                      ║
║ ┌────────────────────────────────────────────────────────────────┐  ║
║ │ Case 2: a8f3c2d1-5e6b-4a2c-8b9f-7d4e1c6a5b3f                  │  ║
║ │ Created: 2026-02-18                                            │  ║
║ ├────────────────────────────────────────────────────────────────┤  ║
║ │ Status: ⏳ PENDING           |  Alert: ROUTINE        │ ⏳ No  │  ║
║ ├────────────────────────────────────────────────────────────────┤  ║
║ │ ▼ 📝 Your Symptoms                                            │  ║
║ │   "I have a persistent cough and mild fever for 3 days"       │  ║
║ │                                                                 │  ║
║ │ ▼ 💬 AI Assessment                                            │  ║
║ │   "Symptoms consistent with upper respiratory infection or     │  ║
║ │    common cold. Recommend home care and monitoring..."         │  ║
║ │                                                                 │  ║
║ │ 🕐 Waiting for nurse review...                                │  ║
║ └────────────────────────────────────────────────────────────────┘  ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## 🎯 Key Features Shown

### ✅ For APPROVED Cases:

1. **Green Status Badge**
   - Shows "✅ APPROVED"
   - Clear visual indicator that case is approved

2. **Expandable Nurse Approval Notes**
   - Title: "👨‍⚕️ Nurse Approval Notes"
   - Shows nurse's full message including:
     - Approval confirmation
     - Required documents for appointment
     - Special instructions
     - Appointment specialist info
     - Any preparation guidelines

3. **Appointment Eligibility**
   - Shows "✅" button in right column
   - Indicates patient CAN book appointment

4. **Complete Case Information**
   - Original symptoms patient described
   - AI assessment
   - Triage category
   - All expandable for easy reading

---

### ⏳ For PENDING Cases:

1. **Orange Status Badge**
   - Shows "⏳ PENDING"
   - Indicates awaiting nurse review

2. **No Appointment Option**
   - Shows "⏳ No" in right column
   - Indicates patient cannot book yet

3. **Basic Case Info Only**
   - Shows symptoms and AI assessment
   - No nurse feedback yet
   - Message: "Waiting for nurse review..."

---

### ❌ For REJECTED Cases:

1. **Red Status Badge**
   - Shows "❌ REJECTED"
   - Clear visual indicator of rejection

2. **Expandable Rejection Feedback**
   - Title: "⚠️ Rejection Feedback"
   - Shows reason for rejection
   - Encourages resubmission
   - Explains next steps

3. **No Appointment Option**
   - Shows "❌ No" in right column
   - Appointment booking disabled

---

## 📋 What Nurse Notes Should Include

When nurses approve a case, they should include:

### Required Documents:
```
"Please bring:
1) Medical history records
2) Latest blood work results
3) Insurance card
4) Photo ID
5) List of current medications"
```

### Specialist Information:
```
"Appointment with Dr. Sarah Johnson
Specialty: Orthopedic Surgery
Date: [will be scheduled separately]"
```

### Pre-Appointment Instructions:
```
"Please do the following before your appointment:
- Avoid strenuous activity
- Keep the area clean and dry
- Avoid applying heat or cold
- Document any changes in symptoms"
```

### Follow-up Information:
```
"After your appointment, please:
- Schedule follow-up within 2-4 weeks
- Keep us updated on treatment progress
- Report any adverse reactions immediately"
```

---

## 🔄 User Journey with Nurse Notes

### Step 1: Patient Submits Symptoms
```
Patient: "I have severe joint pain and stiffness"
System: ✅ Creates case, sends to nurse review
```

### Step 2: Patient Checks Status (Pending)
```
Case Status: ⏳ PENDING
Notes: (none yet)
Action: Wait for nurse review
```

### Step 3: Nurse Reviews and Approves
```
Nurse: Reviews case, AI assessment
Nurse: Clicks "Approve"
Nurse: Types detailed notes with requirements
```

### Step 4: Patient Sees Approval + Instructions
```
Case Status: ✅ APPROVED
Notes: ✅ "Approved for specialist consultation.
           Please bring: 1) Medical history records
           2) Latest blood work results..."
Action: Can now book appointment
```

### Step 5: Patient Books Appointment
```
Patient: Opens "Book Appointment" tab
Patient: Form is now ENABLED (was disabled before)
Patient: Fills out: type, date, specialist, reason
Patient: Submits appointment request
```

---

## 💡 Benefits of This System

1. **Clear Communication**
   - Nurse's instructions are explicit and visible
   - No confusion about what to bring
   - Professional appearance

2. **Better Patient Preparation**
   - Patients know exactly what documents needed
   - Can prepare ahead of time
   - Reduces appointment delays

3. **Reduced No-Shows**
   - Clear instructions improve compliance
   - Patients understand importance
   - Better prepared = higher attendance

4. **Audit Trail**
   - All nurse comments saved in database
   - Compliant with healthcare regulations
   - Can reference what was discussed

5. **Professional Workflow**
   - Proper handoff between AI and nurse
   - Nurse can customize care plan
   - Patient gets personalized attention

---

## ✅ All Features Working

- ✅ Nurse notes saved to database
- ✅ Patient retrieves notes via API
- ✅ Notes displayed in expandable section
- ✅ Formatted professionally with icon
- ✅ Color-coded by status (green/orange/red)
- ✅ Appointment booking gated on approval
- ✅ Rejection feedback also displayed
- ✅ Complete case history available

**System Status: READY FOR PRODUCTION** ✅
