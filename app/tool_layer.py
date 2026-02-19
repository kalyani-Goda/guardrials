"""
Tool Layer: Appointment Scheduling with Authorization & Validation
Implements secure tool execution with Arcade authorization and Pydantic validation
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from pydantic import BaseModel, Field, validator, ValidationError
import jwt

from config.settings import get_settings
from config.logging_config import logger


class AppointmentType(str, Enum):
    """Types of medical appointments"""
    PRIMARY_CARE = "primary_care"
    SPECIALIST = "specialist"
    EMERGENCY = "emergency"
    FOLLOW_UP = "follow_up"
    VIRTUAL = "virtual"


class AppointmentStatus(str, Enum):
    """Appointment statuses"""
    REQUESTED = "requested"
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class AppointmentRequest(BaseModel):
    """Pydantic model for appointment requests with validation"""

    patient_id: str = Field(..., description="Patient identifier")
    date: datetime = Field(..., description="Appointment date and time")
    reason: str = Field(..., min_length=10, max_length=500, description="Reason for appointment")
    appointment_type: AppointmentType = Field(
        default=AppointmentType.PRIMARY_CARE,
        description="Type of appointment"
    )
    preferred_specialist: Optional[str] = Field(
        default=None,
        description="Preferred specialist type if applicable"
    )
    insurance_id: Optional[str] = Field(
        default=None,
        description="Patient insurance ID"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Additional notes"
    )

    @validator("date")
    def validate_date(cls, v: datetime) -> datetime:
        """Validate appointment date is in the future"""
        now = datetime.utcnow()

        # Must be at least 1 hour in the future
        min_time = now + timedelta(hours=1)
        if v < min_time:
            raise ValueError(f"Appointment must be at least 1 hour in the future. Provided: {v}")

        # Cannot be more than 1 year in the future
        max_time = now + timedelta(days=365)
        if v > max_time:
            raise ValueError(f"Appointment cannot be more than 1 year in the future")

        return v

    @validator("patient_id")
    def validate_patient_id(cls, v: str) -> str:
        """Validate patient ID format"""
        if not v or len(v) < 5:
            raise ValueError("Invalid patient ID format")
        return v.strip()

    @validator("reason")
    def validate_reason(cls, v: str) -> str:
        """Validate appointment reason"""
        # Check for dangerous keywords
        dangerous_keywords = ["suicide", "harm", "kill", "die"]
        if any(keyword in v.lower() for keyword in dangerous_keywords):
            raise ValueError("Safety concern detected. Please call 911 or contact crisis services.")
        return v.strip()


class AppointmentAuthorizer:
    """
    Authorizes appointment requests against authenticated user context
    Prevents confused deputy vulnerability
    """

    def __init__(self):
        """Initialize authorizer"""
        settings = get_settings()
        self.secret_key = settings.SECRET_KEY

    def authorize_appointment_request(
        self,
        token: str,
        request: AppointmentRequest
    ) -> tuple[bool, Optional[str]]:
        """
        Authorize appointment request against JWT token

        Args:
            token: JWT token from authenticated user
            request: AppointmentRequest to authorize

        Returns:
            Tuple of (is_authorized, error_message)
        """
        try:
            # Decode and verify JWT token
            decoded = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            token_patient_id = decoded.get("patient_id")
            token_user_id = decoded.get("user_id")

            # CRITICAL: Confused Deputy Check
            # Verify the patient_id in request matches the authenticated user's patient_id
            if request.patient_id != token_patient_id:
                logger.critical(
                    "CONFUSED DEPUTY ATTEMPT DETECTED",
                    extra={"extra_fields": {
                        "authenticated_patient_id": token_patient_id,
                        "requested_patient_id": request.patient_id,
                        "user_id": token_user_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }}
                )
                return False, "Authorization failed: Patient ID mismatch"

            # Verify token is not expired
            exp_time = decoded.get("exp")
            if exp_time and datetime.utcfromtimestamp(exp_time) < datetime.utcnow():
                logger.warning(
                    "Expired token used",
                    extra={"extra_fields": {"user_id": token_user_id}}
                )
                return False, "Token expired. Please re-authenticate."

            logger.info(
                "Appointment request authorized",
                extra={"extra_fields": {
                    "patient_id": request.patient_id,
                    "appointment_type": request.appointment_type.value
                }}
            )
            return True, None

        except jwt.InvalidTokenError as e:
            logger.warning(
                f"Invalid token: {str(e)}",
                extra={"extra_fields": {"error": str(e)}}
            )
            return False, "Invalid authentication token"

        except Exception as e:
            logger.error(
                f"Authorization error: {str(e)}",
                extra={"extra_fields": {"error": str(e)}}
            )
            return False, "Authorization error occurred"

    def generate_token(self, patient_id: str, user_id: str, expires_in: int = 3600) -> str:
        """
        Generate JWT token for patient

        Args:
            patient_id: Patient identifier
            user_id: User identifier
            expires_in: Token expiration time in seconds

        Returns:
            JWT token string
        """
        payload = {
            "patient_id": patient_id,
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
            "iat": datetime.utcnow(),
        }
        token = jwt.encode(payload, self.secret_key, algorithm="HS256")
        return token


class EHRIntegration:
    """Integration with Electronic Health Record system"""

    def __init__(self):
        """Initialize EHR integration"""
        settings = get_settings()
        self.ehr_api_base_url = settings.EHR_API_BASE_URL
        self.ehr_api_key = settings.EHR_API_KEY
        self.timeout = settings.EHR_API_TIMEOUT

    def book_appointment(self, request: AppointmentRequest) -> Dict[str, Any]:
        """
        Book appointment in EHR system

        Args:
            request: Validated AppointmentRequest

        Returns:
            Dict with booking confirmation details
        """
        # In production, this would call the actual EHR API
        # For now, simulate the booking
        booking_result = {
            "success": True,
            "appointment_id": f"APT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{request.patient_id[-4:]}",
            "patient_id": request.patient_id,
            "date": request.date.isoformat(),
            "type": request.appointment_type.value,
            "status": AppointmentStatus.SCHEDULED.value,
            "confirmation_number": f"CONF-{request.patient_id}-{request.date.strftime('%Y%m%d')}",
            "ehr_reference": f"EHR-{datetime.utcnow().timestamp()}",
            "created_at": datetime.utcnow().isoformat(),
        }

        logger.info(
            "Appointment booked successfully",
            extra={"extra_fields": {
                "appointment_id": booking_result["appointment_id"],
                "patient_id": request.patient_id,
                "type": request.appointment_type.value,
                "date": request.date.isoformat()
            }}
        )

        return booking_result

    def cancel_appointment(self, appointment_id: str, reason: str) -> Dict[str, Any]:
        """Cancel an existing appointment"""
        logger.info(
            "Appointment cancelled",
            extra={"extra_fields": {
                "appointment_id": appointment_id,
                "reason": reason
            }}
        )
        return {
            "success": True,
            "appointment_id": appointment_id,
            "status": AppointmentStatus.CANCELLED.value,
            "cancelled_at": datetime.utcnow().isoformat(),
        }

    def get_available_slots(
        self,
        appointment_type: AppointmentType,
        days_ahead: int = 14
    ) -> List[Dict[str, Any]]:
        """Get available appointment slots"""
        slots = []
        start_date = datetime.utcnow() + timedelta(hours=1)

        # Generate mock available slots
        for day_offset in range(days_ahead):
            for hour in [9, 11, 13, 15]:  # Mock available hours
                slot_time = start_date + timedelta(days=day_offset, hours=hour)
                slots.append({
                    "time": slot_time.isoformat(),
                    "type": appointment_type.value,
                    "available": True,
                })

        return slots[:5]  # Return first 5 available slots


class AppointmentSchedulingTool:
    """
    Main tool for secure appointment scheduling
    Combines validation, authorization, and EHR integration
    """

    def __init__(self):
        """Initialize scheduling tool"""
        self.authorizer = AppointmentAuthorizer()
        self.ehr = EHRIntegration()
        logger.info("Appointment Scheduling Tool initialized")

    def schedule_appointment(
        self,
        appointment_data: Dict[str, Any],
        auth_token: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Schedule appointment with full validation and authorization

        Args:
            appointment_data: Raw appointment data from user
            auth_token: JWT authentication token
            session_id: Session identifier

        Returns:
            Dict with scheduling result
        """
        result = {
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "success": False,
            "error": None,
            "validation_errors": [],
            "authorization_error": None,
            "appointment": None,
        }

        # Step 1: Validate request structure
        try:
            request = AppointmentRequest(**appointment_data)
        except ValidationError as e:
            result["validation_errors"] = [
                {"field": err["loc"][0], "message": err["msg"]}
                for err in e.errors()
            ]
            logger.warning(
                "Appointment validation failed",
                extra={"extra_fields": {
                    "session_id": session_id,
                    "errors": result["validation_errors"]
                }}
            )
            result["error"] = "Invalid appointment request. Please correct the errors."
            return result

        # Step 2: Authorize request
        is_authorized, auth_error = self.authorizer.authorize_appointment_request(
            auth_token,
            request
        )

        if not is_authorized:
            result["authorization_error"] = auth_error
            logger.error(
                "Appointment authorization failed",
                extra={"extra_fields": {
                    "session_id": session_id,
                    "error": auth_error
                }}
            )
            result["error"] = auth_error
            return result

        # Step 3: Book appointment in EHR
        try:
            booking_result = self.ehr.book_appointment(request)
            result["success"] = True
            result["appointment"] = booking_result
            logger.info(
                "Appointment scheduled successfully",
                extra={"extra_fields": {
                    "session_id": session_id,
                    "appointment_id": booking_result["appointment_id"]
                }}
            )
        except Exception as e:
            result["error"] = f"Failed to book appointment: {str(e)}"
            logger.error(
                "EHR booking failed",
                extra={"extra_fields": {
                    "session_id": session_id,
                    "error": str(e)
                }}
            )

        return result

    def get_available_appointments(
        self,
        appointment_type: str,
        days_ahead: int = 14
    ) -> List[Dict[str, Any]]:
        """Get available appointment slots"""
        try:
            app_type = AppointmentType(appointment_type)
            return self.ehr.get_available_slots(app_type, days_ahead)
        except ValueError:
            logger.warning(f"Invalid appointment type: {appointment_type}")
            return []

    def cancel_appointment(
        self,
        appointment_id: str,
        auth_token: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Cancel appointment with authorization"""
        # Verify token before cancellation
        try:
            decoded = jwt.decode(auth_token, self.authorizer.secret_key, algorithms=["HS256"])
            result = self.ehr.cancel_appointment(
                appointment_id,
                reason="User requested cancellation"
            )
            result["session_id"] = session_id
            return result
        except jwt.InvalidTokenError:
            return {
                "success": False,
                "error": "Authorization failed",
                "session_id": session_id
            }


# Global instance
_scheduling_tool: Optional[AppointmentSchedulingTool] = None


def get_scheduling_tool() -> AppointmentSchedulingTool:
    """Get or create the scheduling tool"""
    global _scheduling_tool
    if _scheduling_tool is None:
        _scheduling_tool = AppointmentSchedulingTool()
    return _scheduling_tool
