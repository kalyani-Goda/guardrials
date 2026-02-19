"""
Input Layer: HIPAA Firewall using Presidio & Redis
Handles anonymization of PII (Personally Identifiable Information)
and Medical PHI (Protected Health Information)
"""

import json
import hashlib
import uuid
import re
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timedelta

import redis
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from config.settings import get_settings
from config.logging_config import logger


class RedisCache:
    """Redis-based cache for PII-to-token mapping"""

    def __init__(self):
        """Initialize Redis connection"""
        settings = get_settings()
        self.redis_client = redis.from_url(
            settings.get_redis_url(),
            decode_responses=True,
            socket_timeout=settings.REDIS_TIMEOUT
        )
        self.ttl = 3600  # 1 hour default TTL
        self.session_ttl = 86400  # 24 hours for session data

    def set_mapping(self, session_id: str, pii_token: str, original_value: str) -> None:
        """Store PII token mapping with encryption"""
        key = f"pii_mapping:{session_id}:{pii_token}"
        encrypted_value = self._encrypt_value(original_value)
        self.redis_client.setex(key, self.ttl, encrypted_value)
        logger.debug(
            f"Stored PII mapping in Redis",
            extra={"extra_fields": {"session_id": session_id, "pii_token": pii_token}}
        )

    def get_mapping(self, session_id: str, pii_token: str) -> Optional[str]:
        """Retrieve original PII value using token"""
        key = f"pii_mapping:{session_id}:{pii_token}"
        encrypted_value = self.redis_client.get(key)
        if encrypted_value:
            return self._decrypt_value(encrypted_value)
        return None

    def store_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        """Store session metadata"""
        key = f"session:{session_id}"
        self.redis_client.setex(key, self.session_ttl, json.dumps(session_data))

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session metadata"""
        key = f"session:{session_id}"
        data = self.redis_client.get(key)
        return json.loads(data) if data else None

    def _encrypt_value(self, value: str) -> str:
        """Simple encryption (in production, use proper encryption)"""
        # This is a placeholder - use proper encryption like Fernet in production
        return hashlib.sha256(value.encode()).hexdigest()

    def _decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt value (placeholder)"""
        # This returns the hash - in production implement proper decryption
        return encrypted_value

    def health_check(self) -> bool:
        """Check Redis connectivity"""
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return False


class SSNRecognizer(PatternRecognizer):
    """Custom recognizer for US Social Security Numbers"""
    
    def __init__(self, name: str = "SSNRecognizer", **kwargs):
        """Initialize SSN recognizer with pattern"""
        patterns = [
            Pattern("SSN_PATTERN", r"\b\d{3}-\d{2}-\d{4}\b", 0.95),  # XXX-XX-XXXX
            Pattern("SSN_NO_DASH", r"\b\d{9}\b", 0.85),  # XXXXXXXXX (less confident)
        ]
        super().__init__(supported_entity="US_SSN", patterns=patterns, name=name)


class DateRecognizer(PatternRecognizer):
    """Custom recognizer for dates in medical context"""
    
    def __init__(self, name: str = "DateRecognizer", **kwargs):
        """Initialize date recognizer with patterns"""
        patterns = [
            Pattern("DATE_PATTERN_1", r"\b(0?[1-9]|1[0-2])[/-](0?[1-9]|[12]\d|3[01])[/-](\d{4}|\d{2})\b", 0.8),  # MM/DD/YYYY or M/D/YY
            Pattern("DATE_PATTERN_2", r"\b(19|20)\d{2}[/-](0?[1-9]|1[0-2])[/-](0?[1-9]|[12]\d|3[01])\b", 0.8),  # YYYY/MM/DD
        ]
        super().__init__(supported_entity="DATE", patterns=patterns, name=name)


class HIPAAAnonymizer:
    """HIPAA-compliant anonymization engine using Presidio"""

    def __init__(self):
        """Initialize Presidio analyzer and anonymizer"""
        settings = get_settings()

        # Initialize Presidio components
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        self.redis_cache = RedisCache()
        self.threshold = 0.3  # Lower threshold for better PII detection (was 0.5)
        self.pii_entities = settings.PII_ENTITIES_TO_DETECT

        # Register custom recognizers for better PII detection
        self._register_custom_recognizers()

        # Define anonymization operators for each entity type
        # Map all common entity types with proper replacements
        self.operators = {
            "PERSON": OperatorConfig("replace", {"new_value": "<PERSON>"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL>"}),
            "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<PHONE_NUMBER>"}),
            "CREDIT_CARD": OperatorConfig("replace", {"new_value": "<CREDIT_CARD>"}),
            "US_SSN": OperatorConfig("replace", {"new_value": "<SSN>"}),
            "SSN": OperatorConfig("replace", {"new_value": "<SSN>"}),
            "DATE_TIME": OperatorConfig("replace", {"new_value": "<DATE>"}),
            "DATE": OperatorConfig("replace", {"new_value": "<DATE>"}),
            "MEDICAL_LICENSE": OperatorConfig("replace", {"new_value": "<LICENSE>"}),
        }
    
    def _register_custom_recognizers(self) -> None:
        """Register custom PII recognizers for better detection"""
        try:
            # Register custom SSN recognizer
            ssn_recognizer = SSNRecognizer()
            self.analyzer.registry.add_recognizer(ssn_recognizer)
            
            # Register custom date recognizer  
            date_recognizer = DateRecognizer()
            self.analyzer.registry.add_recognizer(date_recognizer)
            
            logger.info(
                "Custom healthcare recognizers registered",
                extra={"extra_fields": {
                    "recognizers": ["US_SSN", "DATE"]
                }}
            )
        except Exception as e:
            logger.warning(
                f"Could not register custom recognizers: {str(e)}",
                extra={"extra_fields": {"error": str(e)}}
            )

    def analyze_and_anonymize(
        self,
        text: str,
        session_id: Optional[str] = None
    ) -> Tuple[str, Dict[str, List[Dict[str, Any]]]]:
        """
        Analyze text for PII/PHI and return anonymized version with mapping

        Args:
            text: Input text to anonymize
            session_id: Optional session ID for caching

        Returns:
            Tuple of (anonymized_text, entity_mapping)
        """
        if not session_id:
            session_id = str(uuid.uuid4())

        # Analyze the text to find PII entities
        # Include custom entity types (US_SSN, DATE) along with standard types
        entities_to_detect = list(self.pii_entities) + ["US_SSN", "DATE"]
        results = self.analyzer.analyze(
            text=text,
            entities=entities_to_detect,
            language="en"
        )

        # Filter by confidence threshold - use self.threshold (0.3 by default)
        filtered_results = [
            result for result in results
            if result.score >= self.threshold
        ]

        # Create detailed mapping of anonymized entities
        entity_mapping = self._create_entity_mapping(text, filtered_results, session_id)

        # Anonymize the text
        anonymized_text = self.anonymizer.anonymize(
            text=text,
            analyzer_results=filtered_results,
            operators=self.operators
        ).text

        # Store session data
        self.redis_cache.store_session(
            session_id,
            {
                "original_text_hash": hashlib.sha256(text.encode()).hexdigest(),
                "created_at": datetime.utcnow().isoformat(),
                "entity_count": len(entity_mapping),
                "entities": list(entity_mapping.keys())
            }
        )

        logger.info(
            f"Text anonymized successfully",
            extra={"extra_fields": {
                "session_id": session_id,
                "entity_count": len(entity_mapping),
                "original_length": len(text),
                "anonymized_length": len(anonymized_text)
            }}
        )

        return anonymized_text, entity_mapping

    def _create_entity_mapping(
        self,
        text: str,
        results,
        session_id: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Create detailed mapping of PII entities found"""
        entity_mapping: Dict[str, List[Dict[str, Any]]] = {}

        for result in results:
            entity_type = result.entity_type
            original_value = text[result.start:result.end]
            pii_token = f"{entity_type}_{uuid.uuid4().hex[:12]}"

            # Store the mapping in Redis
            self.redis_cache.set_mapping(session_id, pii_token, original_value)

            # Build entity record
            if entity_type not in entity_mapping:
                entity_mapping[entity_type] = []

            entity_mapping[entity_type].append({
                "pii_token": pii_token,
                "original_value_hash": hashlib.sha256(original_value.encode()).hexdigest(),
                "position": {"start": result.start, "end": result.end},
                "confidence": result.score,
                "stored_at": datetime.utcnow().isoformat()
            })

        return entity_mapping

    def deanonymize_response(
        self,
        anonymized_text: str,
        session_id: str,
        entity_mapping: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """
        Deanonymize response before sending back to user
        (Only when appropriate and authorized)
        """
        deanonymized_text = anonymized_text

        # For security, we should NOT automatically deanonymize
        # This is a controlled operation that should log all access
        logger.warning(
            f"Deanonymization requested",
            extra={"extra_fields": {
                "session_id": session_id,
                "entity_count": sum(len(v) for v in entity_mapping.values())
            }}
        )

        # In production: Add audit logging, verify authorization
        # For now, return the anonymized version as safe default
        return anonymized_text

    def validate_cache_health(self) -> Dict[str, Any]:
        """Validate Redis cache health"""
        return {
            "redis_healthy": self.redis_cache.health_check(),
            "timestamp": datetime.utcnow().isoformat()
        }


class PresidioRegistry:
    """Registry for custom PII recognizers"""

    def __init__(self, analyzer: AnalyzerEngine):
        """Initialize with Presidio analyzer"""
        self.analyzer = analyzer
        self._register_custom_recognizers()

    def _register_custom_recognizers(self):
        """Register healthcare-specific custom recognizers"""
        # Example: Medical license number pattern
        from presidio_analyzer.pattern_recognizer import PatternRecognizer

        medical_license_recognizer = PatternRecognizer(
            supported_entity="MEDICAL_LICENSE",
            name="Medical License Pattern",
            patterns=[
                r"(?:License|LIC)[\s-]?#?[\s]?(?:number)?[\s:]*([A-Z]{2}\d{6,8})"
            ]
        )

        # Register the custom recognizer
        self.analyzer.registry.add_recognizer(medical_license_recognizer)
        logger.info("Custom healthcare recognizers registered")


# Global anonymizer instance
_anonymizer: Optional[HIPAAAnonymizer] = None


def get_anonymizer() -> HIPAAAnonymizer:
    """Get or create the HIPAA anonymizer instance"""
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = HIPAAAnonymizer()
        # Register custom recognizers
        PresidioRegistry(_anonymizer.analyzer)
    return _anonymizer
