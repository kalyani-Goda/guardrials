"""Tests for complete agent integration"""

import pytest
from datetime import datetime
from app.agent import MediTriageAgent, get_agent


class TestMediTriageAgent:
    """Test suite for complete agent integration"""

    @pytest.fixture
    def agent(self):
        """Provide agent instance"""
        return MediTriageAgent()

    def test_agent_initialization(self, agent):
        """Test agent initializes all layers"""
        assert agent.anonymizer is not None
        assert agent.dialog_orchestrator is not None
        assert agent.reasoning_engine is not None
        assert agent.scheduling_tool is not None
        assert agent.workflow_orchestrator is not None

    def test_process_emergency_interaction(self, agent):
        """Test emergency detection in complete workflow"""
        result = agent.process_patient_interaction(
            raw_user_input="I have severe chest pain and can't breathe",
            user_id="USER-001"
        )

        assert result["error"] is None
        assert "input_layer" in result["layers_processed"]
        assert "dialog_layer" in result["layers_processed"]
        assert "911" in result["final_response"].upper()

    def test_process_normal_interaction(self, agent):
        """Test normal triage workflow"""
        result = agent.process_patient_interaction(
            raw_user_input="I have a sore throat and mild fever for 2 days",
            user_id="USER-001"
        )

        assert result["error"] is None
        assert "input_layer" in result["layers_processed"]
        assert "dialog_layer" in result["layers_processed"]
        assert "reasoning_layer" in result["layers_processed"]
        assert result["workflow_state"] is not None

    def test_process_off_topic_interaction(self, agent):
        """Test off-topic input handling"""
        result = agent.process_patient_interaction(
            raw_user_input="What's your favorite color?",
            user_id="USER-001"
        )

        assert result["error"] is None
        assert "dialog_layer" in result["layers_processed"]
        # Should not proceed to reasoning for off-topic
        assert "reasoning_layer" not in result["layers_processed"]

    def test_pii_anonymization_in_workflow(self, agent):
        """Test that PII is properly anonymized"""
        result = agent.process_patient_interaction(
            raw_user_input="I'm John Doe, born 05/12/1980, SSN 123-45-6789, with chest pain",
            user_id="USER-001"
        )

        assert result["pii_entities_detected"] > 0
        # Verify PII is not in the workflow state (it should be anonymized)
        workflow_state = result.get("workflow_state", {})
        state_text = str(workflow_state)
        assert "John Doe" not in state_text
        assert "123-45-6789" not in state_text

    def test_dialog_result_in_response(self, agent):
        """Test dialog layer results in response"""
        result = agent.process_patient_interaction(
            raw_user_input="I have a sore throat",
            user_id="USER-001"
        )

        assert "dialog_result" in result
        assert result["dialog_result"]["alert_level"] == "normal"
        assert result["dialog_result"]["routing_decision"] == "PROCEED_TO_TRIAGE"

    def test_reasoning_result_in_response(self, agent):
        """Test reasoning layer output in response"""
        result = agent.process_patient_interaction(
            raw_user_input="I have persistent cough and shortness of breath",
            user_id="USER-001"
        )

        if "reasoning_layer" in result["layers_processed"]:
            assert "reasoning_result" in result
            assert "faithfulness_score" in result["reasoning_result"]
            assert "triage_category" in result["reasoning_result"]

    def test_workflow_state_creation(self, agent):
        """Test workflow state is created for non-emergency cases"""
        result = agent.process_patient_interaction(
            raw_user_input="I need medical attention for my back pain",
            user_id="USER-001"
        )

        assert result["workflow_state"] is not None
        assert "session_id" in result["workflow_state"]
        assert "user_id" in result["workflow_state"]

    def test_interrupt_creation_for_review(self, agent):
        """Test that interrupts are created for nurse review"""
        result = agent.process_patient_interaction(
            raw_user_input="I've been having headaches for a week",
            user_id="USER-001"
        )

        if "interrupt_created" in result:
            assert "interrupt_id" in result["interrupt_created"]
            assert result["interrupt_created"]["status"] == "pending_nurse_review"

    def test_handle_nurse_approval(self, agent):
        """Test nurse approval workflow"""
        # First, get an interaction with interrupt
        interaction_result = agent.process_patient_interaction(
            raw_user_input="I have joint pain",
            user_id="USER-001"
        )

        if "interrupt_created" in interaction_result:
            interrupt_id = interaction_result["interrupt_created"]["interrupt_id"]

            # Test approval
            approval_result = agent.handle_nurse_approval(
                interrupt_id=interrupt_id,
                nurse_id="NURSE-001",
                action="approve",
                notes="Approved for routine appointment"
            )

            assert approval_result["success"] is True
            assert "final_response" in approval_result

    def test_handle_nurse_modification(self, agent):
        """Test nurse can modify response before approval"""
        interaction_result = agent.process_patient_interaction(
            raw_user_input="I have digestive issues",
            user_id="USER-001"
        )

        if "interrupt_created" in interaction_result:
            interrupt_id = interaction_result["interrupt_created"]["interrupt_id"]

            modifications = {
                "final_response": "Modified response: Please see a gastroenterologist"
            }

            modification_result = agent.handle_nurse_approval(
                interrupt_id=interrupt_id,
                nurse_id="NURSE-001",
                action="modify",
                modifications=modifications,
                notes="Modified based on patient history"
            )

            assert modification_result["success"] is True
            assert "Modified response" in modification_result["final_response"]

    def test_get_pending_reviews(self, agent):
        """Test retrieval of pending nurse reviews"""
        # Create some interactions
        agent.process_patient_interaction(
            raw_user_input="I need appointment for checkup",
            user_id="USER-001"
        )

        pending = agent.get_pending_nurse_reviews()
        assert isinstance(pending, list)

    def test_agent_status_report(self, agent):
        """Test agent status reporting"""
        status = agent.get_agent_status()

        assert "status" in status
        assert "redis_healthy" in status
        assert "pending_nurse_reviews" in status
        assert "layers_initialized" in status
        assert len(status["layers_initialized"]) == 5

    def test_error_handling(self, agent):
        """Test graceful error handling"""
        # Test with invalid input
        result = agent.process_patient_interaction(
            raw_user_input=None,
            user_id="USER-001"
        )

        # Should handle error gracefully
        assert "final_response" in result
        assert "error" in result or "could not" in result["final_response"].lower()


class TestGlobalAgent:
    """Test global agent singleton"""

    def test_get_global_agent(self):
        """Test singleton pattern for agent"""
        agent1 = get_agent()
        agent2 = get_agent()
        assert agent1 is agent2

    def test_global_agent_all_layers_initialized(self):
        """Test global agent has all layers"""
        agent = get_agent()
        assert agent.anonymizer is not None
        assert agent.dialog_orchestrator is not None
        assert agent.reasoning_engine is not None
        assert agent.scheduling_tool is not None
        assert agent.workflow_orchestrator is not None
