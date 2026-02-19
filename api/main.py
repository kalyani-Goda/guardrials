"""
FastAPI Server for Medi-Triage Agent
Provides REST endpoints for patient interactions, appointments, and monitoring
"""

from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging
import uuid

from app.agent import get_agent
from app.tool_layer import AppointmentAuthorizer
from config.logging_config import logger
from config.settings import get_settings

# Initialize FastAPI app
app = FastAPI(
    title="Medi-Triage Agent API",
    description="HIPAA-compliant healthcare triage system with 5-layer guardrails",
    version="1.0.0"
)

# Add CORS middleware for Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get settings
settings = get_settings()

# ============================================================
# Pydantic Models for Request/Response
# ============================================================

class PatientInteractionRequest(BaseModel):
    """Request model for patient interaction"""
    user_id: str = Field(..., description="Patient/User ID")
    message: str = Field(..., description="Patient's message/symptoms")
    auth_token: Optional[str] = Field(None, description="Optional JWT token")
    session_id: Optional[str] = Field(None, description="Optional session ID for tracking")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "PATIENT-001",
                "message": "I have severe chest pain and can't catch my breath",
                "auth_token": "optional_jwt_token",
                "session_id": "optional_session_id"
            }
        }


class PatientInteractionResponse(BaseModel):
    """Response model for patient interaction"""
    interaction_id: str
    timestamp: str
    user_id: str
    status: str
    alert_level: Optional[str] = None
    routing_decision: Optional[str] = None
    triage_category: Optional[str] = None
    pii_detected: int
    final_response: str
    layers_processed: List[str]
    pending_nurse_review: bool
    interrupt_id: Optional[str] = None
    # New: Safety check fields
    content_is_safe: bool = True
    safety_risk_level: Optional[str] = None
    safety_issues: List[str] = []


class SafetyIssue(BaseModel):
    """Model for a detected safety issue"""
    type: str = Field(..., description="PROMPT_INJECTION, OFF_TOPIC, PROHIBITED_CONTENT, OTHER_PERSON_INFO")
    severity: str = Field(..., description="HIGH, MEDIUM, CRITICAL")
    description: str = Field(..., description="Description of the issue")
    pattern: str = Field(..., description="Regex pattern that matched")


class AppointmentRequest(BaseModel):
    """Request model for appointment scheduling"""
    patient_id: str = Field(..., description="Patient ID")
    appointment_date: str = Field(..., description="ISO format date")
    appointment_type: str = Field(..., description="Type: primary_care, specialist, emergency")
    reason: str = Field(..., description="Reason for appointment")
    preferred_specialist: Optional[str] = None


class AppointmentResponse(BaseModel):
    """Response model for appointment"""
    success: bool
    appointment_id: Optional[str] = None
    confirmation_number: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None


class TokenRequest(BaseModel):
    """Request model for JWT token generation"""
    patient_id: str = Field(..., description="Patient ID")
    user_id: str = Field(..., description="User ID")
    expires_in: int = Field(3600, description="Seconds until expiration")


class TokenResponse(BaseModel):
    """Response model for token"""
    token: str
    expires_in: int
    expires_at: str


class NurseApprovalRequest(BaseModel):
    """Request model for nurse approval"""
    interrupt_id: str = Field(..., description="Interrupt ID to approve/reject")
    nurse_id: str = Field(..., description="Nurse identifier")
    action: str = Field(..., description="approve or reject")
    notes: Optional[str] = Field(None, description="Approval notes")


class NurseApprovalResponse(BaseModel):
    """Response model for nurse approval"""
    success: bool
    interrupt_id: str
    action: str
    final_response: Optional[str] = None
    error: Optional[str] = None


class AgentStatusResponse(BaseModel):
    """Response model for agent status"""
    status: str
    redis_healthy: bool
    database_healthy: bool
    pending_nurse_reviews: int
    layers_initialized: List[str]
    timestamp: str


class CaseStatusResponse(BaseModel):
    """Response model for case status"""
    interrupt_id: str
    patient_id: str
    status: str  # pending, approved, rejected
    alert_level: str
    triage_category: Optional[str]
    original_message: str
    ai_assessment: str
    created_at: str
    updated_at: Optional[str]
    nurse_notes: Optional[str] = ""
    nurse_id: Optional[str] = None
    human_approved: bool
    human_rejected: bool
    rejection_reason: Optional[str] = None
    appointment_available: bool  # Can schedule appointment (only if approved)


class PatientHistoryResponse(BaseModel):
    """Response model for patient interaction history"""
    user_id: str
    total_interactions: int
    cases: List[CaseStatusResponse]


# ============================================================
# Dependency Injection
# ============================================================

def get_medi_agent():
    """Dependency to get agent instance"""
    return get_agent()


def get_authorizer():
    """Dependency to get appointment authorizer"""
    return AppointmentAuthorizer()


# ============================================================
# API Endpoints
# ============================================================

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API status"""
    return {
        "name": "Medi-Triage Agent API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", tags=["Health"])
async def health_check(agent = Depends(get_medi_agent)):
    """Health check endpoint"""
    try:
        status = agent.get_agent_status()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "redis": "healthy" if status['redis_healthy'] else "unhealthy",
            "database": "healthy"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.post("/api/v1/patient/interact", 
          response_model=PatientInteractionResponse,
          tags=["Patient Interaction"],
          summary="Process patient symptom description")
async def patient_interaction(
    request: PatientInteractionRequest,
    background_tasks: BackgroundTasks,
    agent = Depends(get_medi_agent)
):
    """
    Process patient interaction through all 5 guardrail layers
    
    **Flow:**
    1. Input Layer: Anonymizes PII using Presidio + Redis
    2. Dialog Layer: Detects emergencies and off-topic content
    3. Reasoning Layer: Retrieves clinical protocols from Chroma DB
    4. Tool Layer: Validates authorization
    5. Workflow Layer: Handles nurse approval for critical cases
    
    **Returns:**
    - Alert level and routing decision
    - Triage category
    - Human review requirement status
    - Safety check results (prompt injection, off-topic detection)
    """
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        logger.info(
            f"Patient interaction request",
            extra={"extra_fields": {
                "user_id": request.user_id,
                "session_id": session_id
            }}
        )
        
        # Process through agent (includes prompt injection check as Layer 0)
        result = agent.process_patient_interaction(
            raw_user_input=request.message,
            user_id=request.user_id,
            auth_token=request.auth_token
        )
        
        # Extract safety check results
        safety_check = result.get("safety_check", {})
        safety_issues = [
            issue.get("description", "Unknown issue") 
            for issue in safety_check.get("detected_issues", [])
        ]
        
        # Determine status based on safety check
        status = "rejected" if not result.get("content_is_safe", True) else "completed"
        
        # Format response
        response = PatientInteractionResponse(
            interaction_id=result.get("interaction_id"),
            timestamp=result.get("timestamp"),
            user_id=request.user_id,
            status=status,
            alert_level=result.get("dialog_result", {}).get("alert_level") if status == "completed" else None,
            routing_decision=result.get("dialog_result", {}).get("routing_decision") if status == "completed" else None,
            triage_category=result.get("reasoning_result", {}).get("triage_category") if status == "completed" else None,
            pii_detected=result.get("pii_entities_detected", 0),
            final_response=result.get("final_response", ""),
            layers_processed=result.get("layers_processed", []),
            pending_nurse_review="interrupt_created" in result,
            interrupt_id=result.get("interrupt_created", {}).get("interrupt_id"),
            # New: Safety check fields
            content_is_safe=result.get("content_is_safe", True),
            safety_risk_level=safety_check.get("risk_level"),
            safety_issues=safety_issues
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Patient interaction error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/patient/{user_id}/history", 
          response_model=PatientHistoryResponse,
          tags=["Patient Data"],
          summary="Get patient interaction history and case status")
async def get_patient_history(
    user_id: str,
    agent = Depends(get_medi_agent)
):
    """Retrieve patient interaction history with case status"""
    try:
        # Get all triage sessions for this patient
        db = agent.workflow_orchestrator.local_db
        sessions = db.get_sessions_by_user(user_id)
        
        cases = []
        for session in sessions:
            # Determine status: rejected > approved > pending
            if session.get("human_rejected"):
                status = "rejected"
            elif session.get("human_approved"):
                status = "approved"
            else:
                status = "pending"
            
            case = CaseStatusResponse(
                interrupt_id=session.get("session_id"),
                patient_id=session.get("user_id"),
                status=status,
                alert_level="URGENT" if session.get("triage_category") == "URGENT" else "ROUTINE",
                triage_category=session.get("triage_category"),
                original_message=session.get("symptoms", "N/A"),
                ai_assessment=session.get("generated_advice", "N/A"),
                created_at=session.get("created_at", ""),
                updated_at=session.get("updated_at", ""),
                nurse_notes=session.get("nurse_notes", ""),
                nurse_id=None,  # Would need to track this
                human_approved=session.get("human_approved", False),
                human_rejected=session.get("human_rejected", False),
                rejection_reason=session.get("rejection_reason"),
                appointment_available=session.get("human_approved", False)
            )
            cases.append(case)
        
        return PatientHistoryResponse(
            user_id=user_id,
            total_interactions=len(sessions),
            cases=cases
        )
    except Exception as e:
        logger.error(f"Error retrieving patient history: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/case/{interrupt_id}/status",
          response_model=CaseStatusResponse,
          tags=["Patient Data"],
          summary="Get status of a specific case by interrupt ID")
async def get_case_status(
    interrupt_id: str,
    agent = Depends(get_medi_agent)
):
    """Get detailed status of a specific case"""
    try:
        db = agent.workflow_orchestrator.local_db
        session = db.get_triage_session_by_interrupt_id(interrupt_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Case not found")
        
        return CaseStatusResponse(
            interrupt_id=interrupt_id,
            patient_id=session.get("user_id"),
            status="approved" if session.get("human_approved") else "pending",
            alert_level="URGENT" if session.get("triage_category") == "URGENT" else "ROUTINE",
            triage_category=session.get("triage_category"),
            original_message=session.get("symptoms", "N/A"),
            ai_assessment=session.get("generated_advice", "N/A"),
            created_at=session.get("created_at", ""),
            updated_at=session.get("updated_at", ""),
            nurse_notes=session.get("nurse_notes", ""),
            nurse_id=None,
            human_approved=session.get("human_approved", False),
            appointment_available=session.get("human_approved", False)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving case status: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/appointment/authorize",
          response_model=TokenResponse,
          tags=["Appointments"],
          summary="Generate JWT token for appointment scheduling")
async def authorize_appointment(
    request: TokenRequest,
    authorizer = Depends(get_authorizer)
):
    """
    Generate JWT token for secure appointment scheduling
    
    **Security:** Token includes patient_id to prevent confused deputy attacks
    """
    try:
        token = authorizer.generate_token(
            patient_id=request.patient_id,
            user_id=request.user_id,
            expires_in=request.expires_in
        )
        
        expires_at = datetime.utcnow() + timedelta(seconds=request.expires_in)
        
        return TokenResponse(
            token=token,
            expires_in=request.expires_in,
            expires_at=expires_at.isoformat()
        )
    except Exception as e:
        logger.error(f"Token generation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/appointment/schedule",
          response_model=AppointmentResponse,
          tags=["Appointments"],
          summary="Schedule appointment with authorization")
async def schedule_appointment(
    request: AppointmentRequest,
    auth_token: Optional[str] = Header(None),
    agent = Depends(get_medi_agent)
):
    """
    Schedule appointment with JWT token verification
    
    **Security Features:**
    - JWT token validation
    - Patient ID verification (prevents confused deputy attacks)
    - Audit logging of all scheduling
    """
    try:
        if not auth_token:
            raise HTTPException(status_code=401, detail="Authorization token required")
        
        appointment_data = {
            "patient_id": request.patient_id,
            "date": request.appointment_date,
            "appointment_type": request.appointment_type,
            "reason": request.reason,
            "preferred_specialist": request.preferred_specialist
        }
        
        result = agent.scheduling_tool.schedule_appointment(
            appointment_data=appointment_data,
            auth_token=auth_token,
            session_id=str(uuid.uuid4())
        )
        
        if result.get("success"):
            appointment = result.get("appointment", {})
            return AppointmentResponse(
                success=True,
                appointment_id=appointment.get("appointment_id"),
                confirmation_number=appointment.get("confirmation_number"),
                status=appointment.get("status")
            )
        else:
            return AppointmentResponse(
                success=False,
                error=result.get("error")
            )
            
    except Exception as e:
        logger.error(f"Appointment scheduling error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/nurse/approve",
          response_model=NurseApprovalResponse,
          tags=["Nurse Workflow"],
          summary="Nurse approval/rejection of triage decisions")
async def nurse_approval(
    request: NurseApprovalRequest,
    agent = Depends(get_medi_agent)
):
    """
    Handle nurse approval/rejection of triage decisions
    
    **Use Case:** After AI triage, critical cases await nurse review
    """
    try:
        result = agent.handle_nurse_approval(
            interrupt_id=request.interrupt_id,
            nurse_id=request.nurse_id,
            action=request.action,
            notes=request.notes or ""
        )
        
        return NurseApprovalResponse(
            success=result.get("success", False),
            interrupt_id=request.interrupt_id,
            action=request.action,
            final_response=result.get("final_response"),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"Nurse approval error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/nurse/pending-reviews", tags=["Nurse Workflow"])
async def get_pending_reviews(
    agent = Depends(get_medi_agent)
):
    """Get all pending nurse reviews"""
    try:
        pending = agent.workflow_orchestrator.get_pending_nurse_reviews()
        return {
            "count": len(pending),
            "pending_reviews": pending
        }
    except Exception as e:
        logger.error(f"Error fetching pending reviews: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/agent/status",
         response_model=AgentStatusResponse,
         tags=["System"])
async def get_agent_status(agent = Depends(get_medi_agent)):
    """Get comprehensive agent status and metrics"""
    try:
        status = agent.get_agent_status()
        return AgentStatusResponse(
            status="operational" if status['redis_healthy'] else "degraded",
            redis_healthy=status['redis_healthy'],
            database_healthy=True,  # Assuming healthy if we can respond
            pending_nurse_reviews=status['pending_nurse_reviews'],
            layers_initialized=status['layers_initialized'],
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================
# Error Handlers
# ============================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    logger.error(f"HTTP Exception: {exc.detail}")
    return {
        "error": True,
        "status_code": exc.status_code,
        "detail": exc.detail,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return {
        "error": True,
        "status_code": 500,
        "detail": "Internal server error",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=settings.LOG_LEVEL.lower()
    )
