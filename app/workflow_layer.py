"""
Human-in-the-Loop Layer: LangGraph-based workflow orchestration
Using local SQLite database instead of Google Cloud Firestore
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json
import uuid

from app.local_database import get_local_database
from config.logging_config import logger


class InterruptType(Enum):
    """Types of workflow interrupts"""
    MEDICAL_ADVICE_REVIEW = "medical_advice_review"
    EMERGENCY_ESCALATION = "emergency_escalation"
    APPOINTMENT_CONFIRMATION = "appointment_confirmation"
    SPECIALIST_REFERRAL = "specialist_referral"
    USER_OVERRIDE = "user_override"


@dataclass
class WorkflowState:
    """Represents the state of a triage workflow"""
    session_id: str
    user_id: str
    timestamp_created: str
    timestamp_updated: str
    current_step: str
    symptoms_reported: str
    anonymized_symptoms: str
    retrieved_protocols: List[Dict[str, Any]]
    generated_advice: Optional[str] = None
    faithfulness_score: Optional[float] = None
    triage_category: Optional[str] = None
    appointed_specialist: Optional[str] = None
    appointment_data: Optional[Dict[str, Any]] = None
    human_review_required: bool = False
    human_reviewer_notes: Optional[str] = None
    human_approval: bool = False
    final_response: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary"""
        return asdict(self)

    def to_json(self) -> str:
        """Convert state to JSON"""
        return json.dumps(self.to_dict(), default=str)


class TriageWorkflowOrchestrator:
    """
    Main orchestrator for the complete triage workflow
    Uses local SQLite database for state persistence
    """

    def __init__(self):
        """Initialize workflow orchestrator with local database"""
        self.local_db = get_local_database()
        self.state_repository = self.local_db  # Add state_repository alias for backward compatibility
        logger.info("Triage Workflow Orchestrator initialized with local SQLite")

    def initiate_workflow(
        self,
        user_id: str,
        anonymized_symptoms: str,
        retrieved_protocols: List[Dict[str, Any]]
    ) -> WorkflowState:
        """Initiate a new triage workflow"""
        session_id = f"TRIAGE-{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()

        state = WorkflowState(
            session_id=session_id,
            user_id=user_id,
            timestamp_created=now,
            timestamp_updated=now,
            current_step="initialization",
            symptoms_reported="",
            anonymized_symptoms=anonymized_symptoms,
            retrieved_protocols=retrieved_protocols,
            metadata={"workflow_version": "1.0", "storage": "local_sqlite"}
        )

        logger.info(
            "Workflow initiated",
            extra={"extra_fields": {
                "session_id": session_id,
                "user_id": user_id
            }}
        )

        return state

    def create_advice_review_interrupt(
        self,
        session_id: str,
        user_id: str,
        generated_advice: str,
        faithfulness_score: float,
        triage_category: str,
        anonymized_symptoms: str
    ) -> str:
        """Create interrupt for medical advice review and save to local DB"""
        interrupt_id = f"INT-{uuid.uuid4().hex[:12]}"

        # Save to local SQLite database
        self.local_db.save_triage_session(
            session_id=session_id,
            user_id=user_id,
            symptoms=anonymized_symptoms,
            anonymized_symptoms=anonymized_symptoms,
            triage_category=triage_category,
            generated_advice=generated_advice,
            faithfulness_score=faithfulness_score,
            metadata={
                "interrupt_id": interrupt_id,
                "status": "pending_nurse_review",
                "created_at": datetime.utcnow().isoformat(),
            }
        )

        logger.warning(
            f"Workflow interrupt created: {triage_category}",
            extra={"extra_fields": {
                "interrupt_id": interrupt_id,
                "session_id": session_id,
                "faithfulness_score": faithfulness_score
            }}
        )

        return interrupt_id

    def create_appointment_confirmation_interrupt(
        self,
        session_id: str,
        user_id: str,
        appointment_data: Dict[str, Any]
    ) -> str:
        """Create interrupt for appointment confirmation"""
        interrupt_id = f"INT-{uuid.uuid4().hex[:12]}"

        logger.warning(
            "Appointment confirmation interrupt created",
            extra={"extra_fields": {
                "interrupt_id": interrupt_id,
                "session_id": session_id,
                "appointment_type": appointment_data.get("appointment_type")
            }}
        )

        return interrupt_id

    def approve_and_send_response(
        self,
        session_id: Optional[str] = None,
        nurse_id: str = None,
        approver_notes: Optional[str] = None,
        interrupt_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Approve interrupt and finalize response
        
        Can be called with either session_id or interrupt_id.
        If interrupt_id is provided, it will be used to look up the session.
        """
        # Resolve session_id from interrupt_id if needed
        if interrupt_id and not session_id:
            session_data = self.local_db.get_triage_session_by_interrupt_id(interrupt_id)
            if session_data:
                session_id = session_data["session_id"]
            else:
                return {"success": False, "error": "Interrupt ID not found"}
        
        success = self.local_db.approve_triage_session(
            session_id=session_id,
            nurse_id=nurse_id,
            notes=approver_notes
        )

        if success:
            session_data = self.local_db.get_triage_session(session_id)
            logger.info(
                "Workflow approved and ready for response",
                extra={"extra_fields": {
                    "session_id": session_id,
                    "nurse_id": nurse_id
                }}
            )

            return {
                "success": True,
                "session_id": session_id,
                "final_response": session_data["generated_advice"],
                "triage_category": session_data["triage_category"]
            }

        return {"success": False, "error": "Session not found"}

    def modify_and_approve_response(
        self,
        session_id: Optional[str] = None,
        nurse_id: str = None,
        modifications: Dict[str, Any] = None,
        approver_notes: Optional[str] = None,
        interrupt_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Modify response and approve interrupt
        
        Can be called with either session_id or interrupt_id.
        If interrupt_id is provided, it will be used to look up the session.
        """
        # Resolve session_id from interrupt_id if needed
        if interrupt_id and not session_id:
            session_data = self.local_db.get_triage_session_by_interrupt_id(interrupt_id)
            if session_data:
                session_id = session_data["session_id"]
            else:
                return {"success": False, "error": "Interrupt ID not found"}
        else:
            session_data = self.local_db.get_triage_session(session_id)
        
        if not session_data:
            return {"success": False, "error": "Session not found"}
        
        # Apply modifications to the session
        if modifications:
            if "generated_advice" in modifications:
                session_data["generated_advice"] = modifications["generated_advice"]
            if "triage_category" in modifications:
                session_data["triage_category"] = modifications["triage_category"]
        
        # Approve the modified response
        success = self.local_db.approve_triage_session(
            session_id=session_id,
            nurse_id=nurse_id,
            notes=approver_notes
        )

        if success:
            logger.info(
                "Workflow modified and approved",
                extra={"extra_fields": {
                    "session_id": session_id,
                    "nurse_id": nurse_id,
                    "modifications": list(modifications.keys()) if modifications else []
                }}
            )

            return {
                "success": True,
                "session_id": session_id,
                "final_response": session_data.get("generated_advice"),
                "triage_category": session_data.get("triage_category"),
                "modifications_applied": list(modifications.keys()) if modifications else []
            }

        return {"success": False, "error": "Failed to approve session"}

    def get_workflow_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get complete workflow history for a user"""
        return self.local_db.get_all_triage_sessions(user_id)
    
    def get_pending_nurse_reviews(self) -> List[Dict[str, Any]]:
        """Get all pending nurse reviews from database"""
        return self.local_db.get_pending_reviews()


# Global instance
_orchestrator: Optional[TriageWorkflowOrchestrator] = None


def get_workflow_orchestrator() -> TriageWorkflowOrchestrator:
    """Get or create the workflow orchestrator"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = TriageWorkflowOrchestrator()
    return _orchestrator