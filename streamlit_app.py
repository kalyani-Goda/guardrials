"""
Streamlit Web Interface for Medi-Triage Agent
Interactive dashboard for patient interactions, monitoring, and nurse workflows
"""

import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any, Optional
import time

# ============================================================
# Page Configuration
# ============================================================

st.set_page_config(
    page_title="Medi-Triage Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 8px;
        padding: 20px;
        margin: 10px 0;
    }
    .alert-critical {
        background-color: #ffebee;
        border-left: 4px solid #c62828;
        padding: 15px;
        border-radius: 4px;
    }
    .alert-warning {
        background-color: #fff3e0;
        border-left: 4px solid #e65100;
        padding: 15px;
        border-radius: 4px;
    }
    .alert-success {
        background-color: #e8f5e9;
        border-left: 4px solid #2e7d32;
        padding: 15px;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# Configuration
# ============================================================

API_BASE_URL = st.secrets.get("api_url", "http://localhost:8000")
REFRESH_INTERVAL = 5  # seconds

# ============================================================
# Utility Functions
# ============================================================

@st.cache_resource
def get_session_state():
    """Initialize session state"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None  # 'patient' or 'nurse'
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    return st.session_state


def api_call(endpoint: str, method: str = "GET", data: Optional[Dict] = None):
    """Make API call to FastAPI backend"""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            return None
            
        if response.status_code in [200, 201]:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Connection Error: {str(e)}")
        return None


def format_triage_level(level: str) -> tuple:
    """Format triage level with color"""
    levels = {
        "CRITICAL": ("🔴 CRITICAL", "#ffebee"),
        "EMERGENCY": ("🟠 EMERGENCY", "#fff3e0"),
        "URGENT": ("🟡 URGENT", "#fffde7"),
        "ROUTINE": ("🟢 ROUTINE", "#e8f5e9")
    }
    return levels.get(level, ("⚪ UNKNOWN", "#f5f5f5"))


# ============================================================
# Pages
# ============================================================

def page_login():
    """Login page"""
    st.title("🏥 Medi-Triage Agent")
    st.subheader("HIPAA-Compliant Healthcare Triage System")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 👤 Patient Login")
        patient_id = st.text_input("Patient ID", key="patient_id_input")
        patient_password = st.text_input("Password", type="password", key="patient_pass")
        
        if st.button("Login as Patient", key="login_patient_btn"):
            st.session_state.authenticated = True
            st.session_state.user_role = "patient"
            st.session_state.user_id = patient_id
            st.rerun()
    
    with col2:
        st.markdown("### 👨‍⚕️ Nurse Login")
        nurse_id = st.text_input("Nurse ID", key="nurse_id_input")
        nurse_password = st.text_input("Password", type="password", key="nurse_pass")
        
        if st.button("Login as Nurse", key="login_nurse_btn"):
            st.session_state.authenticated = True
            st.session_state.user_role = "nurse"
            st.session_state.user_id = nurse_id
            st.rerun()
    
    # Info section
    st.divider()
    st.markdown("""
    ### 🛡️ Five-Layer Security Architecture
    
    1. **Input Layer**: PII anonymization using Presidio + Redis
    2. **Dialog Layer**: Emergency detection and topic control
    3. **Reasoning Layer**: Clinical guidelines (Chroma DB RAG)
    4. **Tool Layer**: JWT authorization and appointment scheduling
    5. **Workflow Layer**: Human nurse approval for critical cases
    
    ### 🔐 Privacy Protection
    - All patient data is anonymized before LLM processing
    - PII-to-token mappings stored in Redis with auto-expiration
    - Full audit logging of all access
    - HIPAA-compliant architecture
    """)


def page_patient_dashboard():
    """Patient interaction dashboard"""
    st.title("👤 Patient Triage Dashboard")
    
    # Header info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Patient ID", st.session_state.user_id)
    with col2:
        st.metric("Current Status", "Active")
    with col3:
        st.metric("Pending Reviews", "0")
    
    st.divider()
    
    # Symptom input
    st.markdown("### 📝 Describe Your Symptoms")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        patient_input = st.text_area(
            "Please describe your symptoms in detail:",
            placeholder="e.g., I have severe chest pain, shortness of breath...",
            height=100,
            label_visibility="collapsed"
        )
    
    with col2:
        st.write("")
        st.write("")
        submit_button = st.button("Submit for Triage", type="primary", use_container_width=True)
    
    # Process submission
    if submit_button and patient_input:
        with st.spinner("🔄 Processing through 5 guardrail layers..."):
            response = api_call(
                "/api/v1/patient/interact",
                method="POST",
                data={
                    "user_id": st.session_state.user_id,
                    "message": patient_input,
                    "session_id": None
                }
            )
        
        if response:
            st.session_state.last_interaction = response
            
            # Check for safety rejection FIRST
            if not response.get("content_is_safe", True):
                st.divider()
                st.markdown("### ❌ Content Safety Check Failed")
                
                # Show security alert with appropriate styling
                safety_issues = response.get("safety_issues", [])
                risk_level = response.get("safety_risk_level", "UNKNOWN")
                
                if risk_level == "BLOCKED":
                    st.error(
                        f"🚨 **SECURITY ALERT**\n\n"
                        f"{response.get('final_response', 'Your request has been blocked.')}\n\n"
                        f"**Reason:** {', '.join(safety_issues) if safety_issues else 'Security policy violation'}"
                    )
                elif risk_level == "WARNING":
                    st.warning(
                        f"⚠️ **WARNING**\n\n"
                        f"{response.get('final_response', 'Your request requires review.')}\n\n"
                        f"**Reason:** {', '.join(safety_issues) if safety_issues else 'Content validation issue'}"
                    )
                
                # Show details in expandable
                with st.expander("🔍 Safety Check Details"):
                    st.write(f"**Risk Level:** {risk_level}")
                    st.write(f"**Detected Issues:** {len(safety_issues)}")
                    for issue in safety_issues:
                        st.write(f"  • {issue}")
                    st.write(f"**Layers Processed:** {response.get('layers_processed', [])}")
                
                return  # Stop processing, don't show triage results
            
            # Display results (only if content is safe)
            st.divider()
            st.markdown("### ✅ Triage Results")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                alert_icon, alert_color = format_triage_level(
                    response.get("alert_level", "ROUTINE")
                )
                st.markdown(f"<div style='background-color:{alert_color}; padding: 20px; border-radius: 8px; text-align: center;'><h3>{alert_icon}</h3></div>", unsafe_allow_html=True)
            
            with col2:
                st.metric("Triage Category", response.get("triage_category", "N/A"))
            
            with col3:
                st.metric("PII Detected & Protected", response.get("pii_detected", 0))
            
            with col4:
                routing = response.get("routing_decision", "STANDARD")
                st.metric("Routing Decision", routing)
            
            st.divider()
            
            # Triage response
            st.markdown("### 📢 Triage Assessment")
            st.info(response.get("final_response", "Processing..."))
            
            # Pending review status
            if response.get("pending_nurse_review"):
                st.warning(
                    f"⏳ **Case Under Nurse Review**\n\n"
                    f"Your triage case has been flagged for human review. "
                    f"A nurse will review and provide final guidance shortly.\n\n"
                    f"Interrupt ID: `{response.get('interrupt_id')}`"
                )
            else:
                st.success("✅ Triage complete. You may proceed with recommended action.")
            
            # Debug info
            with st.expander("ℹ️ Processing Details"):
                st.write("**Layers Processed:**", response.get("layers_processed", []))
                st.write("**Interaction ID:**", response.get("interaction_id"))
                st.write("**Timestamp:**", response.get("timestamp"))
                if response.get("safety_issues"):
                    st.write("**Safety Check Result:** PASSED (No issues)")


def page_nurse_dashboard():
    """Nurse review and approval dashboard"""
    st.title("👨‍⚕️ Nurse Review Dashboard")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Nurse ID", st.session_state.user_id)
    with col2:
        st.metric("Current Status", "On Duty")
    with col3:
        refresh_button = st.button("🔄 Refresh")
    
    st.divider()
    
    # Fetch pending reviews
    with st.spinner("Loading pending reviews..."):
        reviews_response = api_call("/api/v1/nurse/pending-reviews")
    
    if reviews_response:
        pending_count = reviews_response.get("count", 0)
        pending_reviews = reviews_response.get("pending_reviews", [])
        
        st.markdown(f"### 📋 Pending Case Reviews ({pending_count})")
        
        if pending_count == 0:
            st.success("✅ All cases reviewed! Great work.")
        else:
            # Display pending cases
            for i, case in enumerate(pending_reviews, 1):
                patient_id = case.get('patient_id') or 'Unknown'
                interrupt_id = case.get('interrupt_id') or 'unknown'
                alert_level = case.get('alert_level', 'ROUTINE')
                
                with st.expander(f"Case {i}: {patient_id} - {alert_level}"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"**Patient ID:** {patient_id}")
                        st.markdown(f"**Alert Level:** {format_triage_level(alert_level)[0]}")
                        st.markdown(f"**Triage Category:** {case.get('triage_category', 'Unknown')}")
                        st.markdown(f"**Original Input:** {case.get('original_message', 'N/A')}")
                        st.markdown(f"**AI Assessment:** {case.get('ai_assessment', 'N/A')}")
                    
                    with col2:
                        st.markdown(f"**Created:** {case.get('created_at', 'N/A')}")
                        st.markdown(f"**Session ID:** {interrupt_id}")
                    
                    st.divider()
                    
                    # Approval actions - create unique key using index
                    col_approve, col_reject, col_notes = st.columns([1, 1, 2])
                    
                    with col_approve:
                        if st.button("✅ Approve", key=f"approve_{i}"):
                            with st.spinner("Processing approval..."):
                                result = api_call(
                                    "/api/v1/nurse/approve",
                                    method="POST",
                                    data={
                                        "interrupt_id": case.get('interrupt_id'),
                                        "nurse_id": st.session_state.user_id,
                                        "action": "approve",
                                        "notes": "Approved by nurse"
                                    }
                                )
                            
                            if result and result.get("success"):
                                st.success("Case approved!")
                                st.rerun()
                            else:
                                st.error("Approval failed")
                    
                    with col_reject:
                        if st.button("❌ Reject", key=f"reject_{i}"):
                            with st.spinner("Processing rejection..."):
                                result = api_call(
                                    "/api/v1/nurse/approve",
                                    method="POST",
                                    data={
                                        "interrupt_id": case.get('interrupt_id'),
                                        "nurse_id": st.session_state.user_id,
                                        "action": "reject",
                                        "notes": "Rejected by nurse"
                                    }
                                )
                            
                            if result and result.get("success"):
                                st.warning("Case rejected and sent for review")
                                st.rerun()
                            else:
                                st.error("Rejection failed")
                    
                    with col_notes:
                        approval_notes = st.text_input(
                            "Approval notes:",
                            key=f"notes_{i}_{case.get('interrupt_id', 'unknown')}"
                        )


def page_system_monitor():
    """System monitoring and health dashboard"""
    st.title("📊 System Monitoring Dashboard")
    
    # Refresh button
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 Refresh Status", use_container_width=True):
            st.rerun()
    
    # Fetch agent status
    with st.spinner("Loading system status..."):
        status = api_call("/api/v1/agent/status")
    
    if status:
        # Status cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            redis_status = "✅ Healthy" if status.get("redis_healthy") else "❌ Down"
            st.metric("Redis Cache", redis_status)
        
        with col2:
            db_status = "✅ Healthy" if status.get("database_healthy") else "❌ Down"
            st.metric("Database", db_status)
        
        with col3:
            st.metric("Overall Status", status.get("status", "unknown").upper())
        
        with col4:
            pending = status.get("pending_nurse_reviews", 0)
            st.metric("Pending Reviews", pending)
        
        st.divider()
        
        # Layers status
        st.markdown("### 🏗️ Initialized Layers")
        layers = status.get("layers_initialized", [])
        
        col1, col2, col3 = st.columns(3)
        layer_list = [
            ("Input Layer", "🔐 Anonymization"),
            ("Dialog Layer", "💬 Emergency Detection"),
            ("Reasoning Layer", "🧠 Clinical Guidelines"),
            ("Tool Layer", "🔧 Authorization"),
            ("Workflow Layer", "👨‍⚕️ Human Review")
        ]
        
        for i, (layer, description) in enumerate(layer_list):
            status_icon = "✅" if layer in layers else "⏳"
            if i % 3 == 0:
                col = col1
            elif i % 3 == 1:
                col = col2
            else:
                col = col3
            
            with col:
                st.info(f"{status_icon} {layer}\n{description}")
        
        st.divider()
        
        # System info
        st.markdown("### ℹ️ System Information")
        st.write(f"**Last Updated:** {status.get('timestamp')}")
        st.write(f"**API Version:** 1.0.0")
        st.write(f"**Architecture:** 5-Layer Guardrail System")


def page_patient_case_status():
    """Patient case status and history page"""
    st.title("📋 Your Case Status & History")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"**Patient ID:** {st.session_state.user_id}")
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    st.divider()
    
    # Fetch patient history
    history = api_call(f"/api/v1/patient/{st.session_state.user_id}/history")
    
    if not history:
        st.info("No cases found. Submit a symptom description to get started.")
        return
    
    total_cases = history.get("total_interactions", 0)
    cases = history.get("cases", [])
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Cases", total_cases)
    
    with col2:
        approved_count = sum(1 for case in cases if case.get("human_approved"))
        st.metric("Approved Cases", approved_count)
    
    with col3:
        pending_count = sum(1 for case in cases if not case.get("human_approved"))
        st.metric("Pending Review", pending_count)
    
    with col4:
        appt_eligible = sum(1 for case in cases if case.get("appointment_available"))
        st.metric("Can Book Appointment", appt_eligible)
    
    st.divider()
    
    if not cases:
        st.info("No cases to display.")
        return
    
    st.markdown("### Recent Cases")
    
    for i, case in enumerate(cases, 1):
        interrupt_id = case.get("interrupt_id", "N/A")
        status = case.get("status", "pending")
        alert_level = case.get("alert_level", "ROUTINE")
        human_approved = case.get("human_approved", False)
        human_rejected = case.get("human_rejected", False)
        
        # Color code based on status
        if status == "approved":
            status_icon = "✅"
            status_color = "#e8f5e9"
        elif status == "rejected":
            status_icon = "❌"
            status_color = "#ffebee"
        else:
            status_icon = "⏳"
            status_color = "#fff3e0"
        
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.markdown(f"**Case {i}:** {interrupt_id[:20]}...")
                st.caption(f"Created: {case.get('created_at', 'N/A')[:10]}")
            
            with col2:
                st.markdown(f"**Status:** {status_icon} {status.upper()}")
                st.markdown(f"**Alert:** {alert_level}")
            
            with col3:
                if status == "approved":
                    st.success("✅ Approved")
                elif status == "rejected":
                    st.error("❌ Rejected")
                else:
                    st.warning("⏳ Pending")
            
            st.divider()
            
            # Case details
            col1, col2 = st.columns(2)
            
            with col1:
                with st.expander("📝 Your Symptoms"):
                    st.write(case.get("original_message", "N/A"))
            
            with col2:
                with st.expander("💬 AI Assessment"):
                    st.write(case.get("ai_assessment", "N/A"))
            
            # Nurse notes/feedback for approved or rejected cases
            if status == "approved" and case.get("nurse_notes"):
                with st.expander("👨‍⚕️ Nurse Approval Notes"):
                    st.success(case.get("nurse_notes"))
            
            # Rejection feedback
            if status == "rejected":
                rejection_reason = case.get("rejection_reason", "No reason provided")
                with st.expander("⚠️ Rejection Feedback"):
                    st.error(f"**Reason:** {rejection_reason}")
                    st.info("Please review the feedback and resubmit if you'd like our team to reconsider.")
            
            # Triage category if available
            if case.get("triage_category"):
                st.write(f"**Triage Category:** {case.get('triage_category')}")


def page_patient_book_appointment():
    """Patient appointment booking page"""
    st.title("📅 Book an Appointment")
    
    st.write(f"**Patient ID:** {st.session_state.user_id}")
    st.divider()
    
    # Fetch patient cases to check appointment eligibility
    history = api_call(f"/api/v1/patient/{st.session_state.user_id}/history")
    
    if not history:
        st.error("No cases found. Please submit a triage request first.")
        return
    
    cases = history.get("cases", [])
    approved_cases = [c for c in cases if c.get("human_approved")]
    
    if not approved_cases:
        st.warning("""
        ⏳ **You need nurse approval before booking an appointment**
        
        Please complete the triage process and wait for nurse review first.
        Once approved, you'll be able to book an appointment.
        """)
        return
    
    st.success(f"✅ You have {len(approved_cases)} approved case(s) and can book an appointment!")
    
    # Appointment form
    st.markdown("### Appointment Details")
    
    col1, col2 = st.columns(2)
    
    with col1:
        appt_type = st.selectbox(
            "Appointment Type",
            ["Primary Care", "Specialist", "Follow-up", "Consultation"],
            label_visibility="visible"
        )
        
        appt_date = st.date_input(
            "Preferred Date",
            min_value=datetime.now().date(),
            value=datetime.now().date() + timedelta(days=7)
        )
    
    with col2:
        specialist = st.text_input("Preferred Specialist (if applicable)")
        reason = st.text_area("Reason for Appointment", height=80)
    
    if st.button("Request Appointment", type="primary", use_container_width=True):
        with st.spinner("Scheduling appointment..."):
            response = api_call(
                "/api/v1/appointment/schedule",
                method="POST",
                data={
                    "patient_id": st.session_state.user_id,
                    "appointment_date": appt_date.isoformat(),
                    "appointment_type": appt_type,
                    "reason": reason,
                    "preferred_specialist": specialist or None
                }
            )
        
        if response and response.get("success"):
            st.success(
                f"✅ Appointment Scheduled!\n\n"
                f"Confirmation #: {response.get('confirmation_number', 'N/A')}\n"
                f"Status: {response.get('status', 'Pending')}"
            )
        else:
            st.error(f"Appointment scheduling failed: {response.get('error') if response else 'Unknown error'}")


# ============================================================
# Main App
# ============================================================

def main():
    """Main application flow"""
    session = get_session_state()
    
    # Sidebar navigation
    if session.authenticated:
        with st.sidebar:
            st.markdown("### 🧭 Navigation")
            
            if session.user_role == "patient":
                page = st.radio(
                    "Select Page",
                    ["Triage", "Case Status", "Book Appointment", "Logout"],
                    label_visibility="collapsed"
                )
            else:  # nurse
                page = st.radio(
                    "Select Page",
                    ["Dashboard", "System Monitor", "Logout"],
                    label_visibility="collapsed"
                )
            
            if page == "Logout":
                session.authenticated = False
                session.user_role = None
                session.user_id = None
                st.rerun()
        
        # Route to appropriate page
        if session.user_role == "patient":
            if page == "Triage":
                page_patient_dashboard()
            elif page == "Case Status":
                page_patient_case_status()
            elif page == "Book Appointment":
                page_patient_book_appointment()
        elif session.user_role == "nurse":
            if page == "System Monitor":
                page_system_monitor()
            else:
                page_nurse_dashboard()
    else:
        page_login()


if __name__ == "__main__":
    main()
