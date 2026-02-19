"""
Example usage scenarios for the Medi-Triage Agent
Demonstrates the five-layer guardrail system in action
"""

from app.agent import get_agent
from app.tool_layer import AppointmentAuthorizer
from config.logging_config import logger
from datetime import datetime, timedelta
import json


def example_1_emergency_detection():
    """Example 1: Emergency Detection & 911 Routing"""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Emergency Detection")
    print("=" * 70)

    agent = get_agent()

    # Simulate patient reporting chest pain
    patient_input = """
    I'm having severe chest pain and I can't catch my breath. 
    This started 10 minutes ago. I'm feeling dizzy too.
    """

    print(f"\n🚑 Patient Input: {patient_input.strip()}")
    print("\n⏳ Processing through guardrail layers...")

    result = agent.process_patient_interaction(
        raw_user_input=patient_input,
        user_id="PATIENT-001"
    )

    print(f"\n✅ Processing Complete:")
    print(f"   Layers processed: {', '.join(result['layers_processed'])}")
    print(f"   Alert Level: {result['dialog_result']['alert_level']}")
    print(f"   Routing Decision: {result['dialog_result']['routing_decision']}")
    print(f"\n📢 Agent Response:\n{result['final_response']}")


def example_2_normal_triage():
    """Example 2: Normal Triage Workflow"""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Normal Symptom Triage")
    print("=" * 70)

    agent = get_agent()

    # Simulate patient reporting common cold
    patient_input = """
    I've had a sore throat for 2 days and now I'm developing a cough. 
    I have a mild fever (99.5°F) and feel generally fatigued. 
    This is my first time experiencing these symptoms.
    """

    print(f"\n🏥 Patient Input: {patient_input.strip()}")
    print("\n⏳ Processing through all 5 guardrail layers...")

    result = agent.process_patient_interaction(
        raw_user_input=patient_input,
        user_id="PATIENT-002"
    )

    print(f"\n✅ Processing Complete:")
    print(f"   Layers processed: {', '.join(result['layers_processed'])}")
    print(f"   Alert Level: {result['dialog_result']['alert_level']}")
    print(f"   Routing Decision: {result['dialog_result']['routing_decision']}")
    
    if "reasoning_result" in result:
        print(f"\n📚 Reasoning Layer:")
        print(f"   Triage Category: {result['reasoning_result']['triage_category']}")
        print(f"   Faithfulness Score: {result['reasoning_result']['faithfulness_score']:.2%}")
        print(f"   Response Valid: {result['reasoning_result']['is_valid']}")

    if "interrupt_created" in result:
        print(f"\n👨‍⚕️ Human-in-the-Loop:")
        print(f"   Interrupt ID: {result['interrupt_created']['interrupt_id']}")
        print(f"   Status: {result['interrupt_created']['status']}")
        print(f"   Pending Nurse Review: {result['interrupt_created']['required_approver']}")

    print(f"\n📢 Provisional Response (awaiting nurse approval):\n{result['final_response']}")

    # Demonstrate nurse approval
    if "interrupt_created" in result:
        print("\n" + "-" * 70)
        print("🔄 Simulating Nurse Review & Approval...")
        print("-" * 70)

        interrupt_id = result["interrupt_created"]["interrupt_id"]
        approval_result = agent.handle_nurse_approval(
            interrupt_id=interrupt_id,
            nurse_id="NURSE-001",
            action="approve",
            notes="Reviewed patient case. Approved for routine appointment with primary care physician."
        )

        if approval_result["success"]:
            print(f"\n✅ Nurse Approval Granted")
            print(f"   Approver: NURSE-001")
            print(f"   Final Response Ready: {approval_result['final_response'][:100]}...")


def example_3_pii_anonymization():
    """Example 3: PII Anonymization & Privacy Protection"""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: HIPAA Firewall - PII Anonymization")
    print("=" * 70)

    agent = get_agent()

    # Patient input with sensitive information
    patient_input = """
    My name is Sarah Johnson. 
    I was born on August 15, 1985. 
    My Social Security Number is 123-45-6789.
    You can reach me at (555) 123-4567 or sarah.johnson@email.com.
    I've been experiencing severe migraine headaches for the past week.
    """

    print(f"\n🔐 Raw Patient Input (with PII):")
    print(patient_input.strip())
    print("\n⏳ Layer 1: Input Layer - Anonymization in progress...")

    result = agent.process_patient_interaction(
        raw_user_input=patient_input,
        user_id="PATIENT-003"
    )

    print(f"\n✅ Anonymization Complete:")
    print(f"   PII Entities Detected: {result['pii_entities_detected']}")
    print(f"   Anonymized Text Sent to LLM: YES")
    print(f"\n🔒 What the LLM Sees (Anonymized):")
    print(f"   Name: <PERSON>")
    print(f"   DOB: <DATE>")
    print(f"   SSN: <SSN>")
    print(f"   Phone: <PHONE_NUMBER>")
    print(f"   Email: <EMAIL>")
    print(f"   Medical Info: Sent as-is (non-PII)")
    print(f"\n✅ Workflow State Created (encrypted):")
    if result["workflow_state"]:
        print(f"   Session ID: {result['workflow_state']['session_id']}")
        print(f"   User ID: {result['workflow_state']['user_id']}")
        print(f"   Status: Protected in encrypted storage")


def example_4_off_topic_rejection():
    """Example 4: Off-Topic Content Detection"""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Off-Topic Detection & Boundary Enforcement")
    print("=" * 70)

    agent = get_agent()

    # Off-topic input
    patient_input = "What's your favorite movie? Can you help me with my homework?"

    print(f"\n❌ Off-Topic Input: '{patient_input}'")
    print("\n⏳ Processing through Dialog Layer...")

    result = agent.process_patient_interaction(
        raw_user_input=patient_input,
        user_id="PATIENT-004"
    )

    print(f"\n🚫 Dialog Layer Result:")
    print(f"   Topic Valid: {result['dialog_result']['topic_valid']}")
    print(f"   Routing Decision: {result['dialog_result']['routing_decision']}")
    print(f"\n📢 Agent Response (stays on topic):\n{result['final_response']}")
    print(f"\n✅ Advanced to Reasoning Layer: NO (blocked by dialog layer)")


def example_5_appointment_authorization():
    """Example 5: Appointment Scheduling with Authorization"""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Secure Appointment Scheduling with Authorization")
    print("=" * 70)

    # Step 1: Generate authentication token
    print("\n🔑 Step 1: Generate Authentication Token")
    print("-" * 70)

    authorizer = AppointmentAuthorizer()
    patient_id = "PAT-12345"
    user_id = "USER-001"

    token = authorizer.generate_token(patient_id, user_id, expires_in=3600)
    print(f"   Patient ID: {patient_id}")
    print(f"   User ID: {user_id}")
    print(f"   JWT Token Generated: {token[:50]}...")
    print(f"   Token Expires In: 3600 seconds")

    # Step 2: Schedule appointment
    print("\n📅 Step 2: Schedule Appointment with Authorization Check")
    print("-" * 70)

    agent = get_agent()
    scheduling_tool = agent.scheduling_tool

    appointment_data = {
        "patient_id": patient_id,
        "date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        "reason": "Follow-up consultation for migraine management",
        "appointment_type": "primary_care",
        "preferred_specialist": None
    }

    print(f"   Appointment Type: {appointment_data['appointment_type']}")
    print(f"   Appointment Date: {appointment_data['date']}")
    print(f"   Reason: {appointment_data['reason']}")

    result = scheduling_tool.schedule_appointment(
        appointment_data=appointment_data,
        auth_token=token,
        session_id="test-session"
    )

    if result["success"]:
        print(f"\n✅ Appointment Scheduled Successfully:")
        print(f"   Appointment ID: {result['appointment']['appointment_id']}")
        print(f"   Status: {result['appointment']['status']}")
        print(f"   Confirmation: {result['appointment']['confirmation_number']}")

    # Step 3: Demonstrate confused deputy prevention
    print("\n\n🔐 Step 3: Demonstrate Confused Deputy Prevention")
    print("-" * 70)

    print(f"   Attacker Token: For patient PAT-OTHER")
    print(f"   Requested Patient: PAT-12345")

    malicious_token = authorizer.generate_token("PAT-OTHER", "ATTACKER", expires_in=3600)

    malicious_appointment = {
        "patient_id": patient_id,  # Trying to book for different patient!
        "date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        "reason": "Unauthorized appointment",
        "appointment_type": "specialist"
    }

    result = scheduling_tool.schedule_appointment(
        appointment_data=malicious_appointment,
        auth_token=malicious_token,
        session_id="attack-session"
    )

    print(f"\n🚫 Authorization Failed (as expected):")
    print(f"   Success: {result['success']}")
    print(f"   Error: {result['error']}")
    print(f"   Status: ATTACK BLOCKED ✅")


def example_6_agent_status():
    """Example 6: Agent Status & Monitoring"""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Agent Health & Status Monitoring")
    print("=" * 70)

    agent = get_agent()
    status = agent.get_agent_status()

    print(f"\n📊 Agent Status Report:")
    print(f"   Overall Status: {status['status']}")
    print(f"   Redis Connectivity: {'✅ Healthy' if status['redis_healthy'] else '❌ Down'}")
    print(f"   Pending Nurse Reviews: {status['pending_nurse_reviews']}")

    print(f"\n🏗️ Initialized Layers:")
    for i, layer in enumerate(status['layers_initialized'], 1):
        print(f"   {i}. {layer}")


def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("MEDI-TRIAGE AGENT: COMPREHENSIVE EXAMPLE SCENARIOS")
    print("=" * 70)

    try:
        # Run examples
        example_1_emergency_detection()
        example_3_pii_anonymization()
        example_4_off_topic_rejection()
        example_2_normal_triage()
        example_5_appointment_authorization()
        example_6_agent_status()

        print("\n" + "=" * 70)
        print("✅ ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print("\n📚 Key Takeaways:")
        print("   ✓ Layer 1: All PII is anonymized before LLM processing")
        print("   ✓ Layer 2: Emergencies trigger 911, off-topic is rejected")
        print("   ✓ Layer 3: Clinical protocols guide triage decisions")
        print("   ✓ Layer 4: Authorization prevents unauthorized access")
        print("   ✓ Layer 5: Human nurses approve all medical advice")

    except Exception as e:
        logger.error(f"Error running examples: {str(e)}")
        print(f"\n❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
