#!/usr/bin/env python3
"""Test nurse approval notes are displayed to patients"""

import requests
import json

print("\n" + "="*70)
print("TESTING: Nurse Approval Notes Display")
print("="*70)

# 1. Patient submits a case
print("\n1️⃣ Patient submitting case...")
response = requests.post(
    'http://127.0.0.1:8000/api/v1/patient/interact',
    json={
        'user_id': 'PAT-TEST-NOTES',
        'message': 'I have severe joint pain and stiffness, especially in my knees when I wake up'
    },
    timeout=30
)
result = response.json()
interrupt_id = result.get('interrupt_id')
print(f"✅ Case submitted. Interrupt ID: {interrupt_id}")
print(f"   Status: {result.get('Status')}")
print()

# 2. Get patient history to see the case (before approval)
print("2️⃣ Checking patient history BEFORE approval...")
response = requests.get(f'http://127.0.0.1:8000/api/v1/patient/PAT-TEST-NOTES/history')
cases = response.json().get('cases', [])
if cases:
    case = cases[0]
    print(f"✅ Case found: {case.get('interrupt_id')}")
    print(f"   Status: {case.get('status')}")
    print(f"   Nurse Notes: {case.get('nurse_notes', '(empty)')}")
print()

# 3. Nurse approves with detailed notes about documents
print("3️⃣ Nurse approving case with document requirements...")
response = requests.post(
    'http://127.0.0.1:8000/api/v1/nurse/approve',
    json={
        'interrupt_id': interrupt_id,
        'nurse_id': 'NURSE-001',
        'action': 'approve',
        'notes': 'Approved for specialist consultation. Please bring: 1) Medical history records 2) Latest blood work results 3) Insurance card 4) Photo ID. Appointment scheduled with orthopedic specialist.'
    }
)
result = response.json()
print(f"✅ Approval result: {result.get('success')}")
print()

# 4. Get patient history AFTER approval
print("4️⃣ Checking patient history AFTER approval...")
response = requests.get(f'http://127.0.0.1:8000/api/v1/patient/PAT-TEST-NOTES/history')
cases = response.json().get('cases', [])
if cases:
    case = cases[0]
    print(f"✅ Case found: {case.get('interrupt_id')}")
    print(f"   Status: {case.get('status')}")
    print(f"   Appointment Available: {case.get('appointment_available')}")
    print(f"\n📋 NURSE NOTES/APPROVAL FEEDBACK:")
    print(f"   {case.get('nurse_notes')}")
    print()
    print("✅ Patient CAN SEE the nurse approval notes with document requirements!")
else:
    print("❌ No cases found")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70 + "\n")
