#!/usr/bin/env python
"""Test the dialog layer directly"""

from app.dialog_layer import DialogFlowOrchestrator

try:
    orchestrator = DialogFlowOrchestrator()
    print("✓ DialogFlowOrchestrator created successfully")
    
    result = orchestrator.process_user_input(
        "I'm having severe chest pain and I can't catch my breath",
        "test-session-001"
    )
    
    print("\n✓ process_user_input completed")
    print(f"Result keys: {result.keys()}")
    print(f"Alert level: {result.get('alert_level')}")
    print(f"Routing decision: {result.get('routing_decision')}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
