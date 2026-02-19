#!/usr/bin/env python3
"""
Test script to verify nurse review functionality with updated database mapping
"""
import json
from app.agent import MediTriageAgent
from app.local_database import LocalDatabase

def test_nurse_review_workflow():
    """Test the complete nurse review workflow"""
    
    # Initialize agent and database
    agent = MediTriageAgent()
    db = LocalDatabase()
    
    print("\n" + "="*80)
    print("NURSE REVIEW WORKFLOW TEST")
    print("="*80)
    
    # Step 1: Create a test patient interaction
    print("\n1. Processing patient interaction...")
    result = agent.process_patient_interaction(
        raw_user_input="I have severe headache and mild fever for 2 days",
        user_id="TEST-PATIENT-001"
    )
    
    print(f"   ✓ Interaction processed")
    print(f"   - Session ID: {result.get('session_id', 'N/A')[:16]}...")
    print(f"   - Alert Level: {result.get('alert_level', 'N/A')}")
    print(f"   - Safe: {result.get('content_is_safe', 'N/A')}")
    
    # Step 2: Get pending reviews from database
    print("\n2. Fetching pending reviews from database...")
    pending_reviews = db.get_pending_reviews()
    print(f"   ✓ Found {len(pending_reviews)} pending review(s)")
    
    if pending_reviews:
        for i, case in enumerate(pending_reviews, 1):
            print(f"\n   Case {i}:")
            print(f"   - interrupt_id: {case.get('interrupt_id')}")
            print(f"   - patient_id: {case.get('patient_id')}")
            print(f"   - triage_category: {case.get('triage_category')}")
            print(f"   - alert_level: {case.get('alert_level')}")
            print(f"   - original_message: {case.get('original_message')[:50]}...")
            print(f"   - ai_assessment: {case.get('ai_assessment')[:50]}...")
            print(f"   - status: {case.get('status')}")
    
    # Step 3: Test lookup by interrupt_id
    print("\n3. Testing lookup by interrupt_id...")
    if pending_reviews:
        interrupt_id = pending_reviews[0]['interrupt_id']
        session = db.get_triage_session_by_interrupt_id(interrupt_id)
        if session:
            print(f"   ✓ Found session by interrupt_id: {interrupt_id[:16]}...")
            print(f"   - user_id: {session.get('user_id')}")
            print(f"   - triage_category: {session.get('triage_category')}")
            print(f"   - human_approved: {session.get('human_approved')}")
        else:
            print(f"   ✗ Could not find session by interrupt_id")
    
    # Step 4: Test nurse approval
    print("\n4. Testing nurse approval workflow...")
    if pending_reviews:
        interrupt_id = pending_reviews[0]['interrupt_id']
        approval_result = agent.handle_nurse_approval(
            interrupt_id=interrupt_id,
            nurse_id="NURSE-001",
            action="approve",
            notes="Approved by nurse"
        )
        
        print(f"   Approval result: {approval_result}")
        if approval_result.get('success'):
            print(f"   ✓ Approval successful")
        else:
            print(f"   ✗ Approval failed: {approval_result.get('error', 'Unknown error')}")
    
    # Step 5: Verify approval was recorded
    print("\n5. Verifying approval was recorded...")
    updated_pending = db.get_pending_reviews()
    print(f"   Pending reviews remaining: {len(updated_pending)}")
    
    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80 + "\n")

if __name__ == "__main__":
    test_nurse_review_workflow()
