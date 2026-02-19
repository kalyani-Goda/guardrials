"""
Application initialization and main integration module
Orchestrates all six layers of the Medi-Triage system
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from uuid import uuid4

from app.input_layer import get_anonymizer
from app.dialog_layer import get_dialog_orchestrator
from app.prompt_injection_layer import get_prompt_injection_detector, SafetyCheckResult
from app.reasoning_layer import get_reasoning_engine
from app.tool_layer import get_scheduling_tool
from app.workflow_layer import get_workflow_orchestrator, WorkflowState

from config.logging_config import logger


class MediTriageAgent:
    """
    Main Medi-Triage Agent orchestrator
    Coordinates all six architectural layers for HIPAA-compliant medical triage
    """

    def __init__(self):
        """Initialize the complete triage agent"""
        # Initialize all layers
        self.prompt_injection_detector = get_prompt_injection_detector()
        self.anonymizer = get_anonymizer()
        self.dialog_orchestrator = get_dialog_orchestrator()
        self.reasoning_engine = get_reasoning_engine()
        self.scheduling_tool = get_scheduling_tool()
        self.workflow_orchestrator = get_workflow_orchestrator()

        logger.info("Medi-Triage Agent initialized with all 6 layers")

    def process_patient_interaction(
        self,
        raw_user_input: str,
        user_id: str,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process complete patient interaction through all guardrail layers

        Args:
            raw_user_input: Raw input from patient
            user_id: Patient/user identifier
            auth_token: JWT authentication token for tool access

        Returns:
            Dict with complete interaction result
        """
        interaction_id = str(uuid4())
        timestamp = datetime.utcnow().isoformat()

        result = {
            "interaction_id": interaction_id,
            "timestamp": timestamp,
            "user_id": user_id,
            "layers_processed": [],
            "final_response": None,
            "error": None,
            "workflow_state": None,
        }

        logger.info(
            "Patient interaction started",
            extra={"extra_fields": {
                "interaction_id": interaction_id,
                "user_id": user_id
            }}
        )

        try:
            # ============================================================
            # LAYER 0: PROMPT INJECTION & SAFETY CHECK (NEW)
            # ============================================================
            session_id = str(uuid4())
            safety_result = self.prompt_injection_detector.detect_prompt_injection(
                raw_user_input,
                user_id=user_id,
                session_id=session_id
            )
            result["layers_processed"].append("prompt_injection_layer")
            result["safety_check"] = safety_result
            result["content_is_safe"] = safety_result["is_safe"]

            logger.info(
                "Prompt Injection Layer: Safety check completed",
                extra={"extra_fields": {
                    "interaction_id": interaction_id,
                    "is_safe": safety_result["is_safe"],
                    "risk_level": safety_result["risk_level"],
                    "issues_detected": len(safety_result["detected_issues"])
                }}
            )

            # If not safe, reject immediately
            if not safety_result["is_safe"]:
                result["final_response"] = SafetyCheckResult(safety_result).get_user_message()
                result["error"] = "REJECTED_BY_SAFETY_CHECK"
                result["recommendation"] = safety_result["recommendation"]

                logger.warning(
                    "Patient interaction rejected at safety check",
                    extra={"extra_fields": {
                        "interaction_id": interaction_id,
                        "user_id": user_id,
                        "reason": safety_result["recommendation"],
                        "issues": safety_result["detected_issues"]
                    }}
                )

                return result

            # ============================================================
            # LAYER 1: INPUT LAYER - HIPAA FIREWALL (Anonymization)
            # ============================================================
            anonymized_text, pii_mapping = self.anonymizer.analyze_and_anonymize(
                raw_user_input,
                session_id=session_id
            )
            result["layers_processed"].append("input_layer")
            result["pii_entities_detected"] = sum(
                len(v) for v in pii_mapping.values()
            )

            logger.info(
                "Input Layer: Anonymization completed",
                extra={"extra_fields": {
                    "interaction_id": interaction_id,
                    "pii_count": result["pii_entities_detected"]
                }}
            )

            # ============================================================
            # LAYER 2: DIALOG LAYER - EMERGENCY DETECTION & TOPIC CONTROL
            # ============================================================
            dialog_result = self.dialog_orchestrator.process_user_input(
                anonymized_text,
                session_id=session_id
            )
            result["layers_processed"].append("dialog_layer")
            result["dialog_result"] = {
                "alert_level": dialog_result["alert_level"],
                "topics": dialog_result["detected_topics"],
                "topic_valid": dialog_result.get("topic_valid", True),
                "routing_decision": dialog_result["routing_decision"],
            }

            logger.info(
                "Dialog Layer: Processing completed",
                extra={"extra_fields": {
                    "interaction_id": interaction_id,
                    "alert_level": dialog_result["alert_level"],
                    "routing": dialog_result["routing_decision"]
                }}
            )

            # Check if routing decision bypasses further processing
            if dialog_result["routing_decision"] in ["EMERGENCY_ROUTING", "OFF_TOPIC_RESPONSE"]:
                result["final_response"] = dialog_result["bot_response"]
                return result

            # If urgent, escalate to human
            if dialog_result["routing_decision"] == "URGENT_ESCALATION":
                result["final_response"] = dialog_result["bot_response"]
                result["requires_human_escalation"] = True
                return result

            # ============================================================
            # LAYER 3: REASONING LAYER - CLINICAL GUIDELINE ADHERENCE
            # ============================================================
            reasoning_result = self.reasoning_engine.generate_triage_response(
                symptom_description=anonymized_text,
                session_id=session_id
            )
            result["layers_processed"].append("reasoning_layer")
            result["reasoning_result"] = {
                "faithfulness_score": reasoning_result["faithfulness_score"],
                "is_valid": reasoning_result["is_valid"],
                "triage_category": reasoning_result["triage_category"],
                "generated_response": reasoning_result["generated_response"],
            }

            logger.info(
                "Reasoning Layer: Triage assessment completed",
                extra={"extra_fields": {
                    "interaction_id": interaction_id,
                    "faithfulness_score": reasoning_result["faithfulness_score"],
                    "triage_category": reasoning_result["triage_category"]
                }}
            )

            # ============================================================
            # LAYER 4: TOOL LAYER - APPOINTMENT SCHEDULING
            # ============================================================
            # Initialize workflow state with reasoning output
            workflow_state = self.workflow_orchestrator.initiate_workflow(
                user_id=user_id,
                anonymized_symptoms=anonymized_text,
                retrieved_protocols=reasoning_result["retrieved_documents"]
            )

            workflow_state.generated_advice = reasoning_result["generated_response"]
            workflow_state.faithfulness_score = reasoning_result["faithfulness_score"]
            workflow_state.triage_category = reasoning_result["triage_category"]
            self.workflow_orchestrator.state_repository.save_state(workflow_state)

            result["layers_processed"].append("tool_layer")
            result["tool_layer"] = {
                "scheduling_available": True,
                "appointment_type": reasoning_result["triage_category"]
            }

            logger.info(
                "Tool Layer: Initialized",
                extra={"extra_fields": {
                    "interaction_id": interaction_id,
                    "session_id": session_id
                }}
            )

            # ============================================================
            # LAYER 5: HUMAN-IN-THE-LOOP - WORKFLOW ORCHESTRATION
            # ============================================================
            interrupt_id = self.workflow_orchestrator.create_advice_review_interrupt(
                session_id=session_id,
                user_id=user_id,
                anonymized_symptoms=anonymized_text,
                generated_advice=reasoning_result["generated_response"],
                faithfulness_score=reasoning_result["faithfulness_score"],
                triage_category=reasoning_result["triage_category"]
            )

            result["layers_processed"].append("workflow_layer")
            result["interrupt_created"] = {
                "interrupt_id": interrupt_id,
                "status": "pending_nurse_review",
                "required_approver": "nurse"
            }

            result["workflow_state"] = workflow_state.to_dict()
            result["final_response"] = (
                f"Thank you for providing your information. "
                f"Based on your symptoms ({reasoning_result['triage_category']} priority), "
                f"a nurse specialist will review your case and respond shortly. "
                f"Session ID: {session_id}"
            )

            logger.info(
                "Patient interaction completed - awaiting nurse review",
                extra={"extra_fields": {
                    "interaction_id": interaction_id,
                    "interrupt_id": interrupt_id,
                    "all_layers_processed": result["layers_processed"]
                }}
            )

        except Exception as e:
            error_msg = f"Error processing patient interaction: {str(e)}"
            result["error"] = error_msg
            result["final_response"] = (
                "We encountered an issue processing your request. "
                "Please try again or contact our support team."
            )

            logger.error(
                error_msg,
                extra={"extra_fields": {
                    "interaction_id": interaction_id,
                    "exception": str(e)
                }}
            )

        return result

    def handle_nurse_approval(
        self,
        interrupt_id: str,
        nurse_id: str,
        action: str = "approve",
        modifications: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle nurse review/approval of generated advice

        Args:
            interrupt_id: ID of the interrupt
            nurse_id: ID of the nurse reviewer
            action: "approve", "modify", or "reject"
            modifications: Changes to workflow (if modifying)
            notes: Nurse notes

        Returns:
            Dict with approval result
        """
        if action == "approve":
            return self.workflow_orchestrator.approve_and_send_response(
                interrupt_id=interrupt_id,
                nurse_id=nurse_id,
                approver_notes=notes
            )
        elif action == "modify":
            return self.workflow_orchestrator.modify_and_approve_response(
                interrupt_id=interrupt_id,
                nurse_id=nurse_id,
                modifications=modifications or {},
                approver_notes=notes
            )
        elif action == "reject":
            # Save rejection to database
            try:
                db = self.workflow_orchestrator.local_db
                rejection_reason = notes or "Rejected by nurse"
                db.reject_triage_session(
                    session_id=interrupt_id,
                    nurse_id=nurse_id,
                    reason=rejection_reason
                )
            except Exception as e:
                logger.error(f"Error saving rejection to database: {str(e)}")
            
            logger.warning(
                "Interrupt rejected by nurse",
                extra={"extra_fields": {
                    "interrupt_id": interrupt_id,
                    "nurse_id": nurse_id,
                    "reason": notes
                }}
            )
            return {
                "success": True,
                "message": "Case rejected. Feedback has been saved and is visible to the patient.",
                "interrupt_id": interrupt_id,
                "action": "reject"
            }
        else:
            return {"success": False, "error": "Invalid action"}

    def get_pending_nurse_reviews(self) -> list:
        """Get all pending items requiring nurse review"""
        return self.workflow_orchestrator.get_pending_nurse_reviews()

    def get_agent_status(self) -> Dict[str, Any]:
        """Get agent health and status"""
        cache_health = self.anonymizer.validate_cache_health()
        pending_reviews = len(self.get_pending_nurse_reviews())

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "redis_healthy": cache_health["redis_healthy"],
            "pending_nurse_reviews": pending_reviews,
            "layers_initialized": [
                "input_layer (HIPAA Firewall)",
                "dialog_layer (Emergency Detection)",
                "reasoning_layer (RAG & Faithfulness)",
                "tool_layer (Appointment Scheduling)",
                "workflow_layer (Human-in-the-Loop)"
            ]
        }


# Global instance
_agent: Optional[MediTriageAgent] = None


def get_agent() -> MediTriageAgent:
    """Get or create the global Medi-Triage Agent"""
    global _agent
    if _agent is None:
        _agent = MediTriageAgent()
    return _agent
