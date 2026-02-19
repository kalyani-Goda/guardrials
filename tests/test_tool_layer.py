"""Tests for Tool Layer (Appointment Scheduling)"""

import pytest
import jwt
from datetime import datetime, timedelta

from app.tool_layer import (
    AppointmentRequest,
    AppointmentAuthorizer,
    AppointmentSchedulingTool,
    AppointmentType,
    get_scheduling_tool
)
from pydantic import ValidationError
from config.settings import get_settings


class TestAppointmentRequest:
    """Test Pydantic validation for appointment requests"""

    def test_valid_appointment_request(self):
        """Test valid appointment request"""
        future_date = datetime.utcnow() + timedelta(days=7)
        request = AppointmentRequest(
            patient_id="PAT-12345",
            date=future_date,
            reason="Consultation for sore throat and fever",
            appointment_type=AppointmentType.PRIMARY_CARE
        )
        assert request.patient_id == "PAT-12345"
        assert request.appointment_type == AppointmentType.PRIMARY_CARE

    def test_reject_past_date(self):
        """Test rejection of past appointment dates"""
        past_date = datetime.utcnow() - timedelta(days=1)
        with pytest.raises(ValidationError):
            AppointmentRequest(
                patient_id="PAT-12345",
                date=past_date,
                reason="Sore throat"
            )

    def test_reject_date_less_than_one_hour_away(self):
        """Test rejection of appointments less than 1 hour away"""
        soon_date = datetime.utcnow() + timedelta(minutes=30)
        with pytest.raises(ValidationError):
            AppointmentRequest(
                patient_id="PAT-12345",
                date=soon_date,
                reason="Sore throat"
            )

    def test_reject_date_more_than_one_year_away(self):
        """Test rejection of appointments too far in the future"""
        far_date = datetime.utcnow() + timedelta(days=400)
        with pytest.raises(ValidationError):
            AppointmentRequest(
                patient_id="PAT-12345",
                date=far_date,
                reason="Sore throat"
            )

    def test_reject_short_patient_id(self):
        """Test rejection of invalid patient IDs"""
        future_date = datetime.utcnow() + timedelta(days=7)
        with pytest.raises(ValidationError):
            AppointmentRequest(
                patient_id="AB",  # Too short
                date=future_date,
                reason="Sore throat"
            )

    def test_reject_short_reason(self):
        """Test rejection of too-short reason"""
        future_date = datetime.utcnow() + timedelta(days=7)
        with pytest.raises(ValidationError):
            AppointmentRequest(
                patient_id="PAT-12345",
                date=future_date,
                reason="sick"  # Too short (< 10 chars)
            )

    def test_reject_dangerous_keywords_in_reason(self):
        """Test rejection of dangerous keywords"""
        future_date = datetime.utcnow() + timedelta(days=7)
        with pytest.raises(ValidationError):
            AppointmentRequest(
                patient_id="PAT-12345",
                date=future_date,
                reason="I want to harm myself and need help"
            )


class TestAppointmentAuthorizer:
    """Test authorization for appointment requests"""

    @pytest.fixture
    def authorizer(self):
        """Provide authorizer instance"""
        return AppointmentAuthorizer()

    def test_valid_token_authorization(self, authorizer):
        """Test valid token authorizes request"""
        patient_id = "PAT-12345"
        token = authorizer.generate_token(patient_id, "USER-789")

        future_date = datetime.utcnow() + timedelta(days=7)
        request = AppointmentRequest(
            patient_id=patient_id,
            date=future_date,
            reason="Sore throat consultation"
        )

        is_authorized, error = authorizer.authorize_appointment_request(token, request)
        assert is_authorized is True
        assert error is None

    def test_reject_confused_deputy_attack(self, authorizer):
        """Test detection of confused deputy vulnerability"""
        # Token for one patient
        token = authorizer.generate_token("PAT-ALICE", "USER-789")

        # Request for different patient
        future_date = datetime.utcnow() + timedelta(days=7)
        request = AppointmentRequest(
            patient_id="PAT-BOB",  # Different from token
            date=future_date,
            reason="Sore throat consultation"
        )

        is_authorized, error = authorizer.authorize_appointment_request(token, request)
        assert is_authorized is False
        assert error is not None
        assert "mismatch" in error.lower()

    def test_reject_expired_token(self, authorizer):
        """Test rejection of expired tokens"""
        # Create expired token
        settings = get_settings()
        payload = {
            "patient_id": "PAT-12345",
            "user_id": "USER-789",
            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, settings.secret_key, algorithm="HS256")

        future_date = datetime.utcnow() + timedelta(days=7)
        request = AppointmentRequest(
            patient_id="PAT-12345",
            date=future_date,
            reason="Sore throat"
        )

        is_authorized, error = authorizer.authorize_appointment_request(token, request)
        assert is_authorized is False

    def test_reject_invalid_token(self, authorizer):
        """Test rejection of invalid tokens"""
        future_date = datetime.utcnow() + timedelta(days=7)
        request = AppointmentRequest(
            patient_id="PAT-12345",
            date=future_date,
            reason="Sore throat"
        )

        is_authorized, error = authorizer.authorize_appointment_request("invalid-token", request)
        assert is_authorized is False

    def test_token_generation(self, authorizer):
        """Test JWT token generation"""
        token = authorizer.generate_token("PAT-12345", "USER-789", expires_in=3600)
        assert token is not None
        assert isinstance(token, str)

        # Verify token can be decoded
        decoded = jwt.decode(
            token,
            authorizer.secret_key,
            algorithms=["HS256"]
        )
        assert decoded["patient_id"] == "PAT-12345"
        assert decoded["user_id"] == "USER-789"


class TestAppointmentSchedulingTool:
    """Test complete scheduling tool"""

    @pytest.fixture
    def scheduling_tool(self):
        """Provide scheduling tool instance"""
        return AppointmentSchedulingTool()

    @pytest.fixture
    def auth_token(self):
        """Provide valid auth token"""
        authorizer = AppointmentAuthorizer()
        return authorizer.generate_token("PAT-12345", "USER-789")

    def test_schedule_appointment_success(self, scheduling_tool, auth_token):
        """Test successful appointment scheduling"""
        future_date = datetime.utcnow() + timedelta(days=7)
        appointment_data = {
            "patient_id": "PAT-12345",
            "date": future_date.isoformat(),
            "reason": "Consultation for sore throat",
            "appointment_type": "primary_care"
        }

        result = scheduling_tool.schedule_appointment(
            appointment_data=appointment_data,
            auth_token=auth_token,
            session_id="test-session"
        )

        assert result["success"] is True
        assert result["appointment"] is not None
        assert "appointment_id" in result["appointment"]

    def test_schedule_appointment_validation_failure(self, scheduling_tool, auth_token):
        """Test appointment scheduling with validation failure"""
        appointment_data = {
            "patient_id": "PAT",  # Invalid - too short
            "date": datetime.utcnow().isoformat(),
            "reason": "sick"  # Invalid - too short
        }

        result = scheduling_tool.schedule_appointment(
            appointment_data=appointment_data,
            auth_token=auth_token,
            session_id="test-session"
        )

        assert result["success"] is False
        assert len(result["validation_errors"]) > 0

    def test_schedule_appointment_authorization_failure(self, scheduling_tool):
        """Test appointment scheduling with authorization failure"""
        authorizer = AppointmentAuthorizer()
        # Token for different patient
        token = authorizer.generate_token("PAT-OTHER", "USER-789")

        future_date = datetime.utcnow() + timedelta(days=7)
        appointment_data = {
            "patient_id": "PAT-12345",  # Different from token
            "date": future_date.isoformat(),
            "reason": "Consultation for sore throat"
        }

        result = scheduling_tool.schedule_appointment(
            appointment_data=appointment_data,
            auth_token=token,
            session_id="test-session"
        )

        assert result["success"] is False
        assert "authorization" in result["error"].lower()

    def test_get_available_appointments(self, scheduling_tool):
        """Test retrieval of available appointment slots"""
        slots = scheduling_tool.get_available_appointments("primary_care", days_ahead=14)
        assert len(slots) > 0
        assert all("time" in slot for slot in slots)

    def test_cancel_appointment(self, scheduling_tool):
        """Test appointment cancellation"""
        authorizer = AppointmentAuthorizer()
        token = authorizer.generate_token("PAT-12345", "USER-789")

        result = scheduling_tool.cancel_appointment(
            appointment_id="APT-TEST-001",
            auth_token=token,
            session_id="test-session"
        )

        assert result["success"] is True


class TestGlobalSchedulingTool:
    """Test global scheduling tool instance"""

    def test_get_global_scheduling_tool(self):
        """Test singleton pattern for scheduling tool"""
        tool1 = get_scheduling_tool()
        tool2 = get_scheduling_tool()
        assert tool1 is tool2
