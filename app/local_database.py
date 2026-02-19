"""
Local SQLite database for persistent storage
Replaces PostgreSQL/Firestore for on-premises deployment
"""

from sqlalchemy import create_engine, Column, String, DateTime, JSON, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import Optional, Dict, Any, List
from config.settings import get_settings
from config.logging_config import logger

Base = declarative_base()


class TriageSession(Base):
    """SQLAlchemy model for triage sessions"""
    __tablename__ = "triage_sessions"

    session_id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    symptoms = Column(String)
    anonymized_symptoms = Column(String)
    triage_category = Column(String)
    generated_advice = Column(String)
    faithfulness_score = Column(Float)
    human_approved = Column(Boolean, default=False)
    human_rejected = Column(Boolean, default=False)
    rejection_reason = Column(String, default=None)
    nurse_notes = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    session_metadata = Column(JSON)


class Appointment(Base):
    """SQLAlchemy model for appointments"""
    __tablename__ = "appointments"

    appointment_id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    specialist = Column(String)
    appointment_date = Column(DateTime)
    status = Column(String, default="scheduled")
    created_at = Column(DateTime, default=datetime.utcnow)
    appointment_metadata = Column(JSON)


class AuditLog(Base):
    """SQLAlchemy model for audit logs (HIPAA compliance)"""
    __tablename__ = "audit_logs"

    log_id = Column(String, primary_key=True)
    action = Column(String)
    user_id = Column(String)
    details = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)


class LocalDatabase:
    """Local SQLite database management"""

    def __init__(self):
        """Initialize SQLite database"""
        settings = get_settings()
        self.engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False}
        )

        # Create all tables
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

        logger.info(f"Local SQLite database initialized: {settings.DATABASE_URL}")

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()

    def save_triage_session(
        self,
        session_id: str,
        user_id: str,
        symptoms: str,
        anonymized_symptoms: str,
        triage_category: str,
        generated_advice: str,
        faithfulness_score: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save triage session to local database"""
        try:
            db = self.get_session()
            session = TriageSession(
                session_id=session_id,
                user_id=user_id,
                symptoms=symptoms,
                anonymized_symptoms=anonymized_symptoms,
                triage_category=triage_category,
                generated_advice=generated_advice,
                faithfulness_score=faithfulness_score,
                session_metadata=metadata
            )
            db.add(session)
            db.commit()

            logger.info(f"Triage session saved locally: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error saving triage session: {str(e)}")
            return False
        finally:
            db.close()

    def get_triage_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve triage session from local database"""
        try:
            db = self.get_session()
            session = db.query(TriageSession).filter(
                TriageSession.session_id == session_id
            ).first()

            if session:
                return {
                    "session_id": session.session_id,
                    "user_id": session.user_id,
                    "triage_category": session.triage_category,
                    "generated_advice": session.generated_advice,
                    "faithfulness_score": session.faithfulness_score,
                    "human_approved": session.human_approved,
                    "nurse_notes": session.nurse_notes,
                    "created_at": session.created_at.isoformat(),
                }
            return None

        except Exception as e:
            logger.error(f"Error retrieving triage session: {str(e)}")
            return None
        finally:
            db.close()

    def get_triage_session_by_interrupt_id(self, interrupt_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve triage session by interrupt_id (can be session_id or stored in session_metadata)"""
        try:
            db = self.get_session()
            
            # First, try to find by session_id directly (most common case)
            session = db.query(TriageSession).filter(
                TriageSession.session_id == interrupt_id
            ).first()
            
            if not session:
                # Fallback: search in session_metadata
                sessions = db.query(TriageSession).all()
                for s in sessions:
                    if s.session_metadata and s.session_metadata.get("interrupt_id") == interrupt_id:
                        session = s
                        break
            
            if not session:
                return None
            
            return {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "triage_category": session.triage_category,
                "generated_advice": session.generated_advice,
                "faithfulness_score": session.faithfulness_score,
                "human_approved": session.human_approved,
                "nurse_notes": session.nurse_notes,
                "created_at": session.created_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Error retrieving triage session by interrupt_id: {str(e)}")
            return None
        finally:
            db.close()

    def get_sessions_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieve all triage sessions for a specific user"""
        try:
            db = self.get_session()
            sessions = db.query(TriageSession).filter(
                TriageSession.user_id == user_id
            ).order_by(TriageSession.created_at.desc()).all()

            result = []
            for session in sessions:
                result.append({
                    "session_id": session.session_id,
                    "user_id": session.user_id,
                    "symptoms": session.symptoms,
                    "triage_category": session.triage_category,
                    "generated_advice": session.generated_advice,
                    "faithfulness_score": session.faithfulness_score,
                    "human_approved": session.human_approved,
                    "human_rejected": session.human_rejected,
                    "rejection_reason": session.rejection_reason,
                    "nurse_notes": session.nurse_notes,
                    "created_at": session.created_at.isoformat() if session.created_at else None,
                    "updated_at": session.updated_at.isoformat() if session.updated_at else None,
                })
            
            return result

        except Exception as e:
            logger.error(f"Error retrieving sessions by user: {str(e)}")
            return []
        finally:
            db.close()

    def save_appointment(
        self,
        appointment_id: str,
        user_id: str,
        specialist: str,
        appointment_date: datetime,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save appointment to local database"""
        try:
            db = self.get_session()
            appointment = Appointment(
                appointment_id=appointment_id,
                user_id=user_id,
                specialist=specialist,
                appointment_date=appointment_date,
                metadata=metadata
            )
            db.add(appointment)
            db.commit()

            logger.info(f"Appointment saved locally: {appointment_id}")
            return True

        except Exception as e:
            logger.error(f"Error saving appointment: {str(e)}")
            return False
        finally:
            db.close()

    def save_audit_log(
        self,
        log_id: str,
        action: str,
        user_id: str,
        details: Dict[str, Any]
    ) -> bool:
        """Save audit log for HIPAA compliance"""
        try:
            db = self.get_session()
            log = AuditLog(
                log_id=log_id,
                action=action,
                user_id=user_id,
                details=details
            )
            db.add(log)
            db.commit()

            logger.info(f"Audit log saved: {action}")
            return True

        except Exception as e:
            logger.error(f"Error saving audit log: {str(e)}")
            return False
        finally:
            db.close()

    def approve_triage_session(
        self,
        session_id: str,
        nurse_id: str,
        notes: Optional[str] = None
    ) -> bool:
        """Mark triage session as human-approved"""
        try:
            db = self.get_session()
            session = db.query(TriageSession).filter(
                TriageSession.session_id == session_id
            ).first()

            if session:
                session.human_approved = True
                session.nurse_notes = notes
                session.updated_at = datetime.utcnow()
                db.commit()

                logger.info(f"Triage session approved by nurse: {nurse_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error approving triage session: {str(e)}")
            return False
        finally:
            db.close()

    def reject_triage_session(
        self,
        session_id: str,
        nurse_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """Mark triage session as rejected by nurse"""
        try:
            db = self.get_session()
            session = db.query(TriageSession).filter(
                TriageSession.session_id == session_id
            ).first()

            if session:
                session.human_rejected = True
                session.rejection_reason = reason or "Rejected by nurse"
                session.updated_at = datetime.utcnow()
                db.commit()

                logger.info(f"Triage session rejected by nurse: {nurse_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error rejecting triage session: {str(e)}")
            return False
        finally:
            db.close()

    def get_all_triage_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all triage sessions for a user"""
        try:
            db = self.get_session()
            sessions = db.query(TriageSession).filter(
                TriageSession.user_id == user_id
            ).order_by(TriageSession.created_at.desc()).all()

            return [
                {
                    "session_id": s.session_id,
                    "triage_category": s.triage_category,
                    "created_at": s.created_at.isoformat(),
                    "human_approved": s.human_approved,
                }
                for s in sessions
            ]

        except Exception as e:
            logger.error(f"Error retrieving triage sessions: {str(e)}")
            return []
        finally:
            db.close()

    def get_pending_reviews(self) -> List[Dict[str, Any]]:
        """Get all triage sessions pending nurse review"""
        try:
            db = self.get_session()
            pending_sessions = db.query(TriageSession).filter(
                TriageSession.human_approved == False
            ).order_by(TriageSession.created_at.asc()).all()

            return [
                {
                    "interrupt_id": s.session_id,  # Map session_id to interrupt_id
                    "patient_id": s.user_id,  # Map user_id to patient_id
                    "triage_category": s.triage_category,
                    "alert_level": "URGENT" if s.triage_category == "URGENT" else "ROUTINE",
                    "original_message": s.symptoms or s.anonymized_symptoms or "N/A",
                    "ai_assessment": s.generated_advice or "No assessment available",
                    "status": "pending",
                    "created_at": s.created_at.isoformat() if s.created_at else "N/A",
                    "human_approved": s.human_approved,
                    "nurse_notes": s.nurse_notes or "",
                    "faithfulness_score": s.faithfulness_score,
                }
                for s in pending_sessions
            ]

        except Exception as e:
            logger.error(f"Error retrieving pending reviews: {str(e)}")
            return []
        finally:
            db.close()
    
    def save_state(self, state) -> bool:
        """Save workflow state to database"""
        try:
            db = self.get_session()
            
            # Check if session already exists
            existing = db.query(TriageSession).filter(
                TriageSession.session_id == state.session_id
            ).first()
            
            if existing:
                # Update existing
                existing.generated_advice = state.generated_advice
                existing.faithfulness_score = state.faithfulness_score
                existing.triage_category = state.triage_category
                db.commit()
            else:
                # Create new
                session = TriageSession(
                    session_id=state.session_id,
                    user_id=state.user_id,
                    symptoms=state.anonymized_symptoms,
                    anonymized_symptoms=state.anonymized_symptoms,
                    triage_category=state.triage_category,
                    generated_advice=state.generated_advice,
                    faithfulness_score=state.faithfulness_score,
                    session_metadata=state.metadata or {}
                )
                db.add(session)
                db.commit()
            
            return True
        except Exception as e:
            logger.error(f"Error saving workflow state: {str(e)}")
            return False
        finally:
            db.close()


# Global instance
_local_db: Optional[LocalDatabase] = None


def get_local_database() -> LocalDatabase:
    """Get or create local database instance"""
    global _local_db
    if _local_db is None:
        _local_db = LocalDatabase()
    return _local_db
