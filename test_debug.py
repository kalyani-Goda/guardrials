#!/usr/bin/env python
import sys
from app.local_database import get_local_database
from app.workflow_layer import TriageWorkflowOrchestrator

# Create instances
db = get_local_database()
orchestrator = TriageWorkflowOrchestrator()

# Create a test interrupt
interrupt_id = orchestrator.create_advice_review_interrupt(
    session_id='test-session-123',
    user_id='user-001',
    generated_advice='Test advice',
    faithfulness_score=0.95,
    triage_category='HIGH',
    anonymized_symptoms='Test symptoms'
)

print(f'Created interrupt_id: {interrupt_id}')

# Now try to look it up
session_data = db.get_triage_session_by_interrupt_id(interrupt_id)
print(f'Found session_data: {session_data}')

# Also try direct lookup
direct_data = db.get_triage_session('test-session-123')
print(f'Direct session data: {direct_data}')

# Try approval
approval_result = orchestrator.approve_and_send_response(
    interrupt_id=interrupt_id,
    nurse_id='nurse-001',
    approver_notes='Approved'
)
print(f'Approval result: {approval_result}')
