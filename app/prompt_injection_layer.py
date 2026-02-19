"""
Prompt Injection & Irrelevant Content Detection Layer
Detects and blocks prompt injection attempts, off-topic queries,
requests for other people's information, and prohibited content
"""

from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import re
from enum import Enum

from config.logging_config import logger
from config.settings import get_settings


class ContentRiskLevel(Enum):
    """Risk levels for detected content"""
    SAFE = "SAFE"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class PromptInjectionDetector:
    """Detects prompt injection, off-topic, and prohibited content"""

    def __init__(self):
        """Initialize detector with patterns and rules"""
        settings = get_settings()
        
        # Prompt injection patterns
        self.prompt_injection_patterns = [
            r"ignore\s+all\s+previous\s+instructions",
            r"forget\s+everything\s+above",
            r"disregard\s+your\s+system\s+prompt",
            r"what\s+are\s+your\s+instructions",
            r"what\s+is\s+your\s+system\s+prompt",
            r"tell\s+me\s+your\s+prompt",
            r"show\s+me\s+your\s+rules",
            r"override\s+your\s+guidelines",
            r"break\s+out\s+of\s+character",
            r"you\s+are\s+no\s+longer\s+a\s+health",
            r"from\s+now\s+on\s+ignore",
            r"jailbreak",
            r"I'm\s+going\s+to\s+try\s+to\s+trick\s+you",
            r"let\s+me\s+test\s+your\s+security",
        ]

        # Off-topic keywords/patterns
        self.off_topic_patterns = [
            # Entertainment/Games
            r"movie\s+recommendations",
            r"game\s+strategies",
            r"sports\s+scores",
            r"celebrity\s+gossip",
            r"joke\s+please",
            # Programming (unless healthcare-related)
            r"write\s+me\s+a\s+python\s+script",
            r"code\s+this\s+function",
            r"debug\s+my\s+java\s+code",
            # Academic dishonesty
            r"write\s+my\s+essay",
            r"homework\s+help",
            r"answer\s+my\s+exam",
            # Financial/Legal (unless healthcare billing)
            r"investment\s+advice",
            r"legal\s+advice",
            r"tax\s+planning",
            # Personal/Social
            r"relationship\s+advice",
            r"how\s+to\s+\w+\s+my\s+partner",
            r"dating\s+tips",
            # General knowledge (unless health-related)
            r"what\s+is\s+the\s+capital\s+of",
            r"who\s+won\s+the\s+world\s+cup",
            r"when\s+was\s+\w+\s+invented",
        ]

        # Prohibited medical topics (dangerous to self-diagnose)
        self.prohibited_medical_patterns = [
            # Serious dangerous conditions
            r"how\s+to\s+commit\s+suicide",
            r"how\s+to\s+harm\s+myself",
            r"overdose\s+on",
            r"cutting\s+myself",
            # Other dangerous
            r"how\s+to\s+poison",
            r"how\s+to\s+create\s+drugs",
            r"how\s+to\s+make\s+explosives",
            # Illegal activities
            r"how\s+to\s+forge",
            r"how\s+to\s+fake\s+prescriptions",
            r"how\s+to\s+buy\s+illegal\s+drugs",
        ]

        # Patterns for requesting other people's info
        self.other_person_patterns = [
            r"what\s+(?:is|can\s+you\s+tell\s+me\s+about)\s+\w+\'s\s+(?:medical|health|diagnosis|condition)",
            r"tell\s+me\s+about\s+\w+\'s\s+symptoms",
            r"can\s+you\s+access\s+\w+\'s\s+medical\s+records",
            r"show\s+me\s+\w+\'s\s+prescription",
            r"what\s+medication\s+(?:is|was)\s+\w+\s+on",
            r"when\s+did\s+\w+\s+(?:get|have)\s+\w+\s+surgery",
            r"doctor\s+said\s+about\s+my\s+(?:mom|dad|brother|sister|friend|spouse)",
            r"my\s+(?:parent|child|relative)\'s\s+(?:test|result|diagnosis)",
        ]

        # Allowed medical topics (these are OK to discuss)
        self.allowed_medical_keywords = [
            "symptom", "pain", "fever", "cough", "headache", "fatigue",
            "nausea", "dizziness", "shortness of breath", "chest pain",
            "rash", "sore throat", "congestion", "vomiting", "diarrhea",
            "medication", "allergy", "injury", "wound", "appointment",
            "diagnosis", "treatment", "follow-up", "physical exam"
        ]

        self.threshold_score = 0.5

    def detect_prompt_injection(
        self,
        text: str,
        user_id: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive prompt injection and irrelevant content detection

        Args:
            text: User input text to analyze
            user_id: User identifier
            session_id: Optional session ID

        Returns:
            Dict with detection results and risk level
        """
        text_lower = text.lower()
        results = {
            "is_safe": True,
            "risk_level": ContentRiskLevel.SAFE.value,
            "detected_issues": [],
            "confidence_score": 0.0,
            "recommendation": "PROCEED",
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id or "N/A"
        }

        # Check 1: Prompt Injection Attempts
        injection_found = self._check_prompt_injection(text_lower)
        if injection_found:
            results["detected_issues"].append({
                "type": "PROMPT_INJECTION",
                "severity": "HIGH",
                "description": "Detected attempt to manipulate system instructions",
                "pattern": injection_found
            })
            results["is_safe"] = False
            results["risk_level"] = ContentRiskLevel.BLOCKED.value
            results["confidence_score"] = 0.95
            results["recommendation"] = "REJECT"

        # Check 2: Off-Topic Detection
        if not injection_found:  # Skip if already blocked
            off_topic_found = self._check_off_topic(text_lower)
            if off_topic_found:
                results["detected_issues"].append({
                    "type": "OFF_TOPIC",
                    "severity": "MEDIUM",
                    "description": "Query is not related to healthcare/medical triage",
                    "pattern": off_topic_found
                })
                results["is_safe"] = False
                results["risk_level"] = ContentRiskLevel.BLOCKED.value
                results["confidence_score"] = 0.90
                results["recommendation"] = "REJECT"

        # Check 3: Prohibited Medical Content
        if not injection_found and not off_topic_found:
            prohibited_found = self._check_prohibited_content(text_lower)
            if prohibited_found:
                results["detected_issues"].append({
                    "type": "PROHIBITED_CONTENT",
                    "severity": "CRITICAL",
                    "description": "Query contains dangerous or illegal medical information request",
                    "pattern": prohibited_found
                })
                results["is_safe"] = False
                results["risk_level"] = ContentRiskLevel.BLOCKED.value
                results["confidence_score"] = 0.98
                results["recommendation"] = "REJECT_AND_ALERT"

        # Check 4: Other People's Information
        if not injection_found and not off_topic_found and not prohibited_found:
            other_person_found = self._check_other_person_request(text_lower)
            if other_person_found:
                results["detected_issues"].append({
                    "type": "OTHER_PERSON_INFO",
                    "severity": "MEDIUM",
                    "description": "Attempting to access medical information about another person",
                    "pattern": other_person_found
                })
                results["is_safe"] = False
                results["risk_level"] = ContentRiskLevel.WARNING.value
                results["confidence_score"] = 0.85
                results["recommendation"] = "WARN_AND_REJECT"

        # If no issues found, set safe
        if results["is_safe"]:
            results["confidence_score"] = 0.98
            results["recommendation"] = "PROCEED"

        # Log detection
        if not results["is_safe"]:
            logger.warning(
                f"Prompt injection/irrelevant content detected",
                extra={"extra_fields": {
                    "user_id": user_id,
                    "session_id": session_id,
                    "risk_level": results["risk_level"],
                    "issues": results["detected_issues"],
                    "confidence": results["confidence_score"]
                }}
            )
        else:
            logger.debug(
                f"Content safety check passed",
                extra={"extra_fields": {
                    "user_id": user_id,
                    "session_id": session_id
                }}
            )

        return results

    def _check_prompt_injection(self, text_lower: str) -> Optional[str]:
        """Check for prompt injection patterns"""
        for pattern in self.prompt_injection_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return pattern
        return None

    def _check_off_topic(self, text_lower: str) -> Optional[str]:
        """Check if query is off-topic (not medical)"""
        # If text contains any off-topic pattern
        for pattern in self.off_topic_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return pattern

        # Check if it's a general question without medical terms
        general_question_patterns = [
            r"^what\s+is",
            r"^who\s+is",
            r"^when\s+was",
            r"^where\s+is",
            r"^how\s+do\s+i\s+(?!manage|treat|help|reduce|relieve|cope|live|prevent|avoid|diagnose)",
        ]

        has_general_question = False
        for pattern in general_question_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                has_general_question = True
                break

        # If it's a general question, check if it has medical keywords
        if has_general_question:
            has_medical_keyword = False
            for keyword in self.allowed_medical_keywords:
                if keyword.lower() in text_lower:
                    has_medical_keyword = True
                    break

            # If general question without medical keywords = off-topic
            if not has_medical_keyword:
                return "General question without medical context"

        return None

    def _check_prohibited_content(self, text_lower: str) -> Optional[str]:
        """Check for prohibited dangerous/illegal medical content"""
        for pattern in self.prohibited_medical_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return pattern
        return None

    def _check_other_person_request(self, text_lower: str) -> Optional[str]:
        """Check for requests about other people's medical info"""
        for pattern in self.other_person_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return pattern

        # Additional check: someone asking "what should [person] do"
        other_person_pronouns = [
            r"my\s+(?:mom|dad|mother|father|parent|brother|sister|sibling|friend|partner|spouse|husband|wife|child|son|daughter|grandparent)",
            r"(?:mom|dad|mother|father|parent|brother|sister|sibling|friend|partner|spouse|husband|wife|child|son|daughter|grandparent)\'s\s+(?:symptoms|condition|diagnosis)",
        ]

        for pattern in other_person_pronouns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                # Check if they're asking for diagnosis/treatment for that person
                if any(word in text_lower for word in ["should", "can", "help", "treat", "medication", "doctor", "what"]):
                    return pattern

        return None


class SafetyCheckResult:
    """Result object for safety checks"""

    def __init__(self, detection_result: Dict[str, Any]):
        self.is_safe = detection_result["is_safe"]
        self.risk_level = detection_result["risk_level"]
        self.detected_issues = detection_result["detected_issues"]
        self.confidence_score = detection_result["confidence_score"]
        self.recommendation = detection_result["recommendation"]
        self.timestamp = detection_result["timestamp"]

    def should_proceed(self) -> bool:
        """Check if input should proceed to next layer"""
        return self.recommendation == "PROCEED"

    def should_alert_human(self) -> bool:
        """Check if human review is needed"""
        return self.recommendation in ["WARN_AND_REJECT", "REJECT_AND_ALERT"]

    def get_user_message(self) -> str:
        """Get appropriate message to show user"""
        if self.recommendation == "PROCEED":
            return "✓ Query validated successfully"

        elif self.recommendation == "REJECT":
            if any(issue["type"] == "PROMPT_INJECTION" for issue in self.detected_issues):
                return (
                    "❌ Security Alert: Your request appears to contain an attempt to manipulate "
                    "the system. Healthcare triage requires honest, direct symptom descriptions. "
                    "Please describe your actual medical symptoms."
                )
            elif any(issue["type"] == "OFF_TOPIC" for issue in self.detected_issues):
                return (
                    "❌ Off-Topic Request: This triage system is for healthcare/medical symptoms only. "
                    "Please describe your medical symptoms or health concerns."
                )
            elif any(issue["type"] == "OTHER_PERSON_INFO" for issue in self.detected_issues):
                return (
                    "❌ Privacy Protection: This system is for your own health information only. "
                    "If concerned about someone else's health, they should contact their own doctor "
                    "or a healthcare provider directly."
                )

        elif self.recommendation == "REJECT_AND_ALERT":
            return (
                "❌ Safety Alert: Your request contains content that cannot be processed through this system. "
                "If you're experiencing a health crisis, please call 911 or contact emergency services immediately."
            )

        elif self.recommendation == "WARN_AND_REJECT":
            return (
                "⚠️ Privacy Alert: Healthcare triage is personalized to YOUR health only. "
                "For concerns about family members or others, please have them use this system directly "
                "or contact their healthcare provider."
            )

        return "❌ Request rejected. Please try again with a valid health concern."


# Global detector instance
_detector: Optional[PromptInjectionDetector] = None


def get_prompt_injection_detector() -> PromptInjectionDetector:
    """Get or create the prompt injection detector instance"""
    global _detector
    if _detector is None:
        _detector = PromptInjectionDetector()
        logger.info("Prompt Injection Detector initialized")
    return _detector
