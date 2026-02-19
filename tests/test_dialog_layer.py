"""Tests for Dialog Layer (Emergency Detection)"""

import pytest
from app.dialog_layer import (
    EmergencyDetector,
    SafeTopicController,
    DialogFlowOrchestrator,
    AlertLevel,
    get_dialog_orchestrator
)


class TestEmergencyDetector:
    """Test suite for emergency detection"""

    @pytest.fixture
    def detector(self):
        """Provide detector instance"""
        return EmergencyDetector()

    def test_detect_chest_pain_emergency(self, detector):
        """Test detection of chest pain as emergency"""
        alert_level, phrase = detector.detect_emergency("I have severe chest pain")
        assert alert_level == AlertLevel.EMERGENCY
        assert phrase == "chest pain"

    def test_detect_breathing_difficulty_emergency(self, detector):
        """Test detection of breathing difficulty"""
        alert_level, phrase = detector.detect_emergency("I'm having trouble breathing")
        assert alert_level == AlertLevel.EMERGENCY

    def test_detect_unconscious_emergency(self, detector):
        """Test detection of unconsciousness"""
        alert_level, phrase = detector.detect_emergency("The patient is unconscious")
        assert alert_level == AlertLevel.EMERGENCY

    def test_detect_heavy_bleeding_emergency(self, detector):
        """Test detection of heavy bleeding"""
        alert_level, phrase = detector.detect_emergency("I'm bleeding heavily from my arm")
        assert alert_level == AlertLevel.EMERGENCY

    def test_detect_urgent_condition(self, detector):
        """Test detection of urgent but not emergency condition"""
        alert_level, phrase = detector.detect_emergency("I have a severe headache")
        # Severe headache alone might not be emergency
        assert alert_level in [AlertLevel.URGENT, AlertLevel.NORMAL]

    def test_detect_no_emergency(self, detector):
        """Test normal input with no emergency"""
        alert_level, phrase = detector.detect_emergency("I have a sore throat")
        assert alert_level == AlertLevel.NORMAL
        assert phrase is None

    def test_case_insensitive_detection(self, detector):
        """Test that detection is case insensitive"""
        alert_level1, _ = detector.detect_emergency("CHEST PAIN")
        alert_level2, _ = detector.detect_emergency("Chest Pain")
        alert_level3, _ = detector.detect_emergency("chest pain")

        assert alert_level1 == alert_level2 == alert_level3 == AlertLevel.EMERGENCY

    def test_get_all_emergency_keywords(self, detector):
        """Test retrieval of all emergency keywords"""
        keywords = detector.get_all_emergency_keywords()
        assert len(keywords) > 0
        assert "chest pain" in keywords


class TestSafeTopicController:
    """Test suite for topic control"""

    @pytest.fixture
    def controller(self):
        """Provide controller instance"""
        return SafeTopicController()

    def test_approve_symptom_topic(self, controller):
        """Test approval of symptom description topic"""
        is_valid, reason = controller.validate_topic("I have a sore throat and cough")
        assert is_valid is True
        assert reason is None

    def test_detect_prohibited_diagnosis_question(self, controller):
        """Test detection of diagnosis questions"""
        is_valid, reason = controller.validate_topic("What disease do I have?")
        assert is_valid is False
        assert reason is not None

    def test_detect_prohibited_medication_request(self, controller):
        """Test detection of medication prescription requests"""
        is_valid, reason = controller.validate_topic("Can you prescribe me antibiotics?")
        assert is_valid is False
        assert reason is not None

    def test_detect_appointment_scheduling_topic(self, controller):
        """Test approval of appointment scheduling"""
        is_valid, reason = controller.validate_topic("I need to schedule an appointment")
        assert is_valid is True

    def test_detect_off_topic_general_chat(self, controller):
        """Test detection of off-topic general chat"""
        is_valid, reason = controller.validate_topic("How's the weather today?")
        assert is_valid is False

    def test_detect_medical_history_topic(self, controller):
        """Test approval of medical history sharing"""
        is_valid, reason = controller.validate_topic("I have a history of diabetes")
        assert is_valid is True

    def test_detect_topics_in_text(self, controller):
        """Test topic detection in text"""
        topics = controller.detect_topics("I have had asthma and need an appointment")
        assert len(topics) > 0

    def test_get_approved_topics(self, controller):
        """Test retrieval of approved topics"""
        topics = controller.APPROVED_TOPICS
        assert "symptoms" in topics
        assert "appointment_scheduling" in topics


class TestDialogFlowOrchestrator:
    """Test suite for complete dialog flow"""

    @pytest.fixture
    def orchestrator(self):
        """Provide orchestrator instance"""
        return DialogFlowOrchestrator()

    def test_emergency_routing(self, orchestrator):
        """Test emergency routing decision"""
        result = orchestrator.process_user_input(
            "I have severe chest pain and can't breathe",
            session_id="test-session-1"
        )

        assert result["alert_level"] == "emergency"
        assert result["routing_decision"] == "EMERGENCY_ROUTING"
        assert "911" in result["bot_response"].upper()

    def test_off_topic_routing(self, orchestrator):
        """Test off-topic response"""
        result = orchestrator.process_user_input(
            "What is the capital of France?",
            session_id="test-session-2"
        )

        assert result["topic_valid"] is False
        assert result["routing_decision"] == "OFF_TOPIC_RESPONSE"

    def test_normal_flow_routing(self, orchestrator):
        """Test normal triage flow"""
        result = orchestrator.process_user_input(
            "I have a sore throat and mild fever",
            session_id="test-session-3"
        )

        assert result["routing_decision"] == "PROCEED_TO_TRIAGE"
        assert result["topic_valid"] is True
        assert result["alert_level"] == "normal"

    def test_urgent_escalation(self, orchestrator):
        """Test urgent condition escalation"""
        result = orchestrator.process_user_input(
            "I have severe head trauma from a fall",
            session_id="test-session-4"
        )

        assert result["routing_decision"] == "URGENT_ESCALATION"
        assert result["requires_human_intervention"] is True

    def test_get_emergency_keywords(self, orchestrator):
        """Test emergency keywords retrieval"""
        keywords = orchestrator.get_emergency_keywords()
        assert "emergency" in keywords
        assert "urgent" in keywords
        assert len(keywords["emergency"]) > 0

    def test_get_prohibited_topics(self, orchestrator):
        """Test prohibited topics retrieval"""
        topics = orchestrator.get_prohibited_topics()
        assert "diagnosis" in topics
        assert "medication_prescription" in topics


class TestGlobalOrchestrator:
    """Test global orchestrator instance"""

    def test_get_global_orchestrator(self):
        """Test singleton pattern for orchestrator"""
        orch1 = get_dialog_orchestrator()
        orch2 = get_dialog_orchestrator()
        assert orch1 is orch2
