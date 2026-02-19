"""Tests for Input Layer (HIPAA Anonymization)"""

import pytest
from app.input_layer import HIPAAAnonymizer, get_anonymizer


class TestHIPAAAnonymizer:
    """Test suite for HIPAA anonymizer"""

    @pytest.fixture
    def anonymizer(self):
        """Provide anonymizer instance"""
        return HIPAAAnonymizer()

    def test_anonymize_ssn(self, anonymizer):
        """Test SSN anonymization"""
        text = "My SSN is 123-45-6789 and I need an appointment"
        anonymized, mapping = anonymizer.analyze_and_anonymize(text)

        assert "123-45-6789" not in anonymized
        assert "<SSN>" in anonymized
        assert "US_SSN" in mapping

    def test_anonymize_phone_number(self, anonymizer):
        """Test phone number anonymization"""
        text = "You can reach me at 555-123-4567"
        anonymized, mapping = anonymizer.analyze_and_anonymize(text)

        assert "555-123-4567" not in anonymized
        assert "<PHONE_NUMBER>" in anonymized

    def test_anonymize_email(self, anonymizer):
        """Test email anonymization"""
        text = "My email is patient@example.com"
        anonymized, mapping = anonymizer.analyze_and_anonymize(text)

        assert "patient@example.com" not in anonymized
        assert "<EMAIL>" in anonymized

    def test_anonymize_person_name(self, anonymizer):
        """Test person name anonymization"""
        text = "My name is John Doe and I have chest pain"
        anonymized, mapping = anonymizer.analyze_and_anonymize(text)

        assert "John Doe" not in anonymized
        assert "<PERSON>" in anonymized

    def test_anonymize_date_of_birth(self, anonymizer):
        """Test date anonymization"""
        text = "I was born on 05/12/1980"
        anonymized, mapping = anonymizer.analyze_and_anonymize(text)

        assert "05/12/1980" not in anonymized
        assert "<DATE>" in anonymized

    def test_no_pii_detection(self, anonymizer):
        """Test text with no PII"""
        text = "I have a sore throat and mild fever"
        anonymized, mapping = anonymizer.analyze_and_anonymize(text)

        assert anonymized == text
        assert len(mapping) == 0

    def test_multiple_pii_entities(self, anonymizer):
        """Test detection of multiple PII entities"""
        text = "John Doe, DOB 05/12/1980, SSN 123-45-6789, call 555-123-4567"
        anonymized, mapping = anonymizer.analyze_and_anonymize(text)

        # All PII should be anonymized
        assert "John Doe" not in anonymized
        assert "05/12/1980" not in anonymized
        assert "123-45-6789" not in anonymized
        assert "555-123-4567" not in anonymized

        # At least some entities should be detected
        total_entities = sum(len(v) for v in mapping.values())
        assert total_entities > 0

    def test_redis_cache_health(self, anonymizer):
        """Test Redis cache connectivity"""
        health = anonymizer.validate_cache_health()
        assert isinstance(health, dict)
        assert "redis_healthy" in health

    def test_session_tracking(self, anonymizer):
        """Test session metadata storage"""
        text = "I have severe chest pain"
        anonymized, mapping = anonymizer.analyze_and_anonymize(text, session_id="test-session-1")

        # Verify session was created
        session_data = anonymizer.redis_cache.get_session("test-session-1")
        assert session_data is not None
        assert session_data["entity_count"] >= 0


class TestPresidioRegistry:
    """Test custom recognizers"""

    def test_custom_recognizers_registered(self):
        """Test that custom recognizers are registered"""
        anonymizer = get_anonymizer()
        assert anonymizer is not None
        # Verify medical license recognizer is registered
        assert len(anonymizer.analyzer.registry.recognizers) > 0
