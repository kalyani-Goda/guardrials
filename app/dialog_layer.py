"""
Dialog Layer: Emergency Detection & Topic Control using NeMo Guardrails
Implements strict conversational boundaries and emergency routing
"""

import re
from typing import List, Dict, Tuple, Optional
from enum import Enum
from datetime import datetime

from config.logging_config import logger


class AlertLevel(Enum):
    """Alert severity levels"""
    EMERGENCY = "emergency"
    URGENT = "urgent"
    NORMAL = "normal"


class EmergencyDetector:
    """Detects emergency conditions from user input"""

    # Critical emergency keywords and phrases
    EMERGENCY_KEYWORDS = {
        "chest pain": AlertLevel.EMERGENCY,
        "chest discomfort": AlertLevel.EMERGENCY,
        "heart attack": AlertLevel.EMERGENCY,
        "trouble breathing": AlertLevel.EMERGENCY,
        "difficulty breathing": AlertLevel.EMERGENCY,
        "shortness of breath": AlertLevel.EMERGENCY,
        "bleeding heavily": AlertLevel.EMERGENCY,
        "uncontrolled bleeding": AlertLevel.EMERGENCY,
        "unconscious": AlertLevel.EMERGENCY,
        "unresponsive": AlertLevel.EMERGENCY,
        "severe allergic reaction": AlertLevel.EMERGENCY,
        "anaphylaxis": AlertLevel.EMERGENCY,
        "choking": AlertLevel.EMERGENCY,
        "severe abdominal pain": AlertLevel.EMERGENCY,
        "poisoning": AlertLevel.EMERGENCY,
        "overdose": AlertLevel.EMERGENCY,
        "stroke": AlertLevel.EMERGENCY,
        "loss of consciousness": AlertLevel.EMERGENCY,
        "severe burns": AlertLevel.EMERGENCY,
        "deep laceration": AlertLevel.EMERGENCY,
        "heavy blood loss": AlertLevel.EMERGENCY,
    }

    # Urgent but not immediately life-threatening
    URGENT_KEYWORDS = {
        "severe pain": AlertLevel.URGENT,
        "severe head trauma": AlertLevel.URGENT,
        "high fever": AlertLevel.URGENT,
        "severe vomiting": AlertLevel.URGENT,
        "loss of vision": AlertLevel.URGENT,
        "paralysis": AlertLevel.URGENT,
        "confusion": AlertLevel.URGENT,
        "difficulty speaking": AlertLevel.URGENT,
    }

    def __init__(self):
        """Initialize emergency detector"""
        self.all_patterns = {**self.EMERGENCY_KEYWORDS, **self.URGENT_KEYWORDS}
        self._compile_regex_patterns()

    def _compile_regex_patterns(self):
        """Pre-compile regex patterns for performance"""
        self.compiled_patterns: Dict[str, Tuple[re.Pattern, AlertLevel]] = {}
        for phrase, level in self.all_patterns.items():
            # Create word boundary regex
            pattern = re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)
            self.compiled_patterns[phrase] = (pattern, level)

    def detect_emergency(self, text: str) -> Tuple[AlertLevel, Optional[str]]:
        """
        Detect emergency conditions in user input

        Args:
            text: User input text

        Returns:
            Tuple of (alert_level, matched_phrase)
        """
        text_lower = text.lower()

        # Check for emergency keywords first (highest priority)
        for phrase, (pattern, level) in self.compiled_patterns.items():
            if level == AlertLevel.EMERGENCY and pattern.search(text):
                logger.warning(
                    "Emergency condition detected",
                    extra={"extra_fields": {"matched_phrase": phrase, "alert_level": level.value}}
                )
                return AlertLevel.EMERGENCY, phrase

        # Check for urgent keywords
        for phrase, (pattern, level) in self.compiled_patterns.items():
            if level == AlertLevel.URGENT and pattern.search(text):
                logger.warning(
                    "Urgent condition detected",
                    extra={"extra_fields": {"matched_phrase": phrase, "alert_level": level.value}}
                )
                return AlertLevel.URGENT, phrase

        return AlertLevel.NORMAL, None

    def get_all_emergency_keywords(self) -> List[str]:
        """Get list of all emergency keywords"""
        return [k for k, v in self.all_patterns.items() if v == AlertLevel.EMERGENCY]

    def get_all_urgent_keywords(self) -> List[str]:
        """Get list of all urgent keywords"""
        return [k for k, v in self.all_patterns.items() if v == AlertLevel.URGENT]


class SafeTopicController:
    """Controls conversation to stay within medical triage boundaries"""

    # Approved conversation topics
    APPROVED_TOPICS = {
        "symptoms": "Medical symptom description and assessment",
        "medical_history": "Relevant medical history and conditions",
        "current_medications": "Current medications and allergies",
        "appointment_scheduling": "Scheduling medical appointments",
        "triage_assessment": "Medical triage and severity assessment",
        "appointment_confirmation": "Confirming appointment details",
    }

    # Prohibited conversation topics
    PROHIBITED_TOPICS = {
        "diagnosis": "We cannot provide medical diagnosis",
        "treatment_advice": "We cannot provide treatment advice",
        "medication_prescription": "We cannot prescribe medications",
        "mental_health": "Mental health concerns require specialist consultation",
        "general_chat": "Please keep conversation focused on medical triage",
        "personal_questions": "We only discuss medical information",
    }

    # Topic detection keywords
    TOPIC_PATTERNS = {
        "symptoms": [
            r"\b(symptom|pain|ache|discomfort|feeling|experience|notice|sore|sick|illness|wound|injury|bleed|trauma|fall|fracture|sprain)\b",
            r"\b(cough|fever|headache|nausea|vomit|rash|throat|cold|flu|wound|burn|cut|fracture|sprain)\b"
        ],
        "medical_history": [
            r"\b(history|had|condition)\b"
        ],
        "current_medications": [
            r"\b(taking|medication|prescription|drug|allergy)\b"
        ],
        "appointment_scheduling": [
            r"\b(appointment|schedule|book|when|available|time)\b"
        ],
        "diagnosis": [
            r"\b(what (do )?i (have|suffer))\b",
            r"\b(what disease|what illness|what condition)\b",
            r"\b(is it|could it be|might i have)\b"
        ],
        "treatment_advice": [
            r"\b(how (do i|should i|can i)|what should|treatment|cure)\b"
        ],
        "medication_prescription": [
            r"\b(prescribe|give me|medicine for)\b"
        ],
    }

    def __init__(self):
        """Initialize topic controller"""
        self._compile_topic_patterns()

    def _compile_topic_patterns(self):
        """Pre-compile topic detection regex patterns"""
        self.compiled_topics: Dict[str, List[re.Pattern]] = {}
        for topic, patterns in self.TOPIC_PATTERNS.items():
            self.compiled_topics[topic] = [re.compile(p, re.IGNORECASE) for p in patterns]

    def detect_topics(self, text: str) -> List[str]:
        """
        Detect conversation topics in user input

        Args:
            text: User input text

        Returns:
            List of detected topics
        """
        detected = []
        for topic, patterns in self.compiled_topics.items():
            for pattern in patterns:
                if pattern.search(text):
                    detected.append(topic)
                    break  # Only add topic once
        return detected

    def validate_topic(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if conversation topic is appropriate

        Args:
            text: User input text

        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        detected_topics = self.detect_topics(text)

        if not detected_topics:
            return False, "Topic not recognized. Please describe your symptoms or medical concerns."

        # Check if ANY detected topic is prohibited
        for topic in detected_topics:
            if topic in self.PROHIBITED_TOPICS:
                reason = self.PROHIBITED_TOPICS[topic]
                logger.info(
                    "Prohibited topic detected",
                    extra={"extra_fields": {"topic": topic, "reason": reason}}
                )
                return False, reason
        
        # Check if at least one topic is in approved topics
        for topic in detected_topics:
            if topic in self.APPROVED_TOPICS:
                logger.info(
                    "Valid topic detected",
                    extra={"extra_fields": {"topics": detected_topics}}
                )
                return True, None

        # If no prohibited topics but no approved topics either, reject
        return False, "Topic not recognized as medical concern. Please describe your symptoms."

    def get_off_topic_response(self, detected_topic: Optional[str]) -> str:
        """Generate appropriate off-topic response"""
        if detected_topic and detected_topic in self.PROHIBITED_TOPICS:
            return f"{self.PROHIBITED_TOPICS[detected_topic]} Please focus on describing your symptoms."
        return "I'm here to help with medical triage and appointment scheduling. Please describe your symptoms or concerns."


class DialogFlowOrchestrator:
    """Orchestrates the dialog flow with emergency detection and topic control"""

    def __init__(self):
        """Initialize orchestrator"""
        self.emergency_detector = EmergencyDetector()
        self.topic_controller = SafeTopicController()

    def process_user_input(self, text: str, session_id: str) -> Dict:
        """
        Process user input through dialog layer guardrails

        Args:
            text: User input
            session_id: Session identifier

        Returns:
            Dict with processing results and routing decision
        """
        result = {
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "input_text": text,
            "alert_level": None,
            "matched_emergency_phrase": None,
            "topic_valid": None,
            "detected_topics": [],
            "routing_decision": None,
            "bot_response": None,
            "requires_human_intervention": False,
        }

        # Step 1: Check for emergency conditions
        alert_level, matched_phrase = self.emergency_detector.detect_emergency(text)
        result["alert_level"] = alert_level.value
        result["matched_emergency_phrase"] = matched_phrase

        if alert_level == AlertLevel.EMERGENCY:
            result["routing_decision"] = "EMERGENCY_ROUTING"
            result["bot_response"] = (
                "🚨 EMERGENCY DETECTED 🚨\n\n"
                "Please hang up and dial 911 immediately.\n"
                "This appears to be a medical emergency requiring immediate emergency response.\n\n"
                "Do not delay. Hang up now and call 911."
            )
            result["requires_human_intervention"] = False  # Route to 911, not human agent
            logger.critical(
                "Emergency detected - routing to 911",
                extra={"extra_fields": {"session_id": session_id, "phrase": matched_phrase}}
            )
            return result

        # Step 2: Check topic validity (unless emergency)
        topic_valid, invalid_reason = self.topic_controller.validate_topic(text)
        result["topic_valid"] = topic_valid
        result["detected_topics"] = self.topic_controller.detect_topics(text)

        if not topic_valid:
            result["routing_decision"] = "OFF_TOPIC_RESPONSE"
            result["bot_response"] = self.topic_controller.get_off_topic_response(
                result["detected_topics"][0] if result["detected_topics"] else None
            )
            logger.info(
                "Off-topic input detected",
                extra={"extra_fields": {"session_id": session_id, "reason": invalid_reason}}
            )
            return result

        # Step 3: Check for urgent conditions
        if alert_level == AlertLevel.URGENT:
            result["routing_decision"] = "URGENT_ESCALATION"
            result["bot_response"] = (
                "I've detected an urgent medical condition. "
                "I'm connecting you with a nurse specialist who can provide immediate assistance."
            )
            result["requires_human_intervention"] = True
            logger.warning(
                "Urgent condition detected - escalating to nurse",
                extra={"extra_fields": {"session_id": session_id, "phrase": matched_phrase}}
            )
            return result

        # Step 4: Normal flow - proceed to reasoning layer
        result["routing_decision"] = "PROCEED_TO_TRIAGE"
        result["bot_response"] = None  # Will be generated by reasoning layer
        logger.info(
            "User input passed dialog layer validation",
            extra={"extra_fields": {
                "session_id": session_id,
                "topics": result["detected_topics"]
            }}
        )

        return result

    def get_emergency_keywords(self) -> Dict[str, List[str]]:
        """Get all emergency and urgent keywords for documentation"""
        return {
            "emergency": self.emergency_detector.get_all_emergency_keywords(),
            "urgent": self.emergency_detector.get_all_urgent_keywords(),
        }

    def get_approved_topics(self) -> Dict[str, str]:
        """Get approved conversation topics"""
        return self.topic_controller.APPROVED_TOPICS

    def get_prohibited_topics(self) -> Dict[str, str]:
        """Get prohibited conversation topics"""
        return self.topic_controller.PROHIBITED_TOPICS


# Global instance
_orchestrator: Optional[DialogFlowOrchestrator] = None


def get_dialog_orchestrator() -> DialogFlowOrchestrator:
    """Get or create the dialog flow orchestrator"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = DialogFlowOrchestrator()
    return _orchestrator
