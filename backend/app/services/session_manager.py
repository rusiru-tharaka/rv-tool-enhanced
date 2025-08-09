"""
Session Management Service
Handles analysis session lifecycle, state management, and persistence
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

# Import models with absolute imports
try:
    from models.core_models import (
        AnalysisSession, 
        AnalysisPhase, 
        SessionStatusResponse,
        PhaseAdvanceResponse
    )
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from models.core_models import (
        AnalysisSession, 
        AnalysisPhase, 
        SessionStatusResponse,
        PhaseAdvanceResponse
    )

class SessionManager:
    """
    Manages analysis sessions for the enhanced UX platform
    In production, this would be backed by Redis or database
    """
    
    def __init__(self):
        # In-memory storage for development
        # TODO: Replace with Redis/Database in production
        self._sessions: Dict[str, AnalysisSession] = {}
    
    def create_session(self, vm_inventory: List[Dict[str, Any]], user_id: Optional[str] = None) -> str:
        """Create a new analysis session"""
        session_id = str(uuid.uuid4())
        
        session = AnalysisSession(
            session_id=session_id,
            user_id=user_id,
            current_phase=AnalysisPhase.MIGRATION_SCOPE,
            vm_inventory=vm_inventory,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            completed_phases=[]
        )
        
        self._sessions[session_id] = session
        return session_id
    
    def get_session(self, session_id: str) -> Optional[AnalysisSession]:
        """Get session by ID"""
        return self._sessions.get(session_id)
    
    def get_session_status(self, session_id: str) -> Optional[SessionStatusResponse]:
        """Get session status for API response"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        return SessionStatusResponse(
            session_id=session.session_id,
            current_phase=session.current_phase,
            completed_phases=session.completed_phases,
            total_vms=len(session.vm_inventory),
            created_at=session.created_at,
            updated_at=session.updated_at
        )
    
    def advance_phase(self, session_id: str, completed_phase_data: Optional[Dict[str, Any]] = None) -> Optional[PhaseAdvanceResponse]:
        """Advance session to next phase"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        # Mark current phase as completed
        if session.current_phase not in session.completed_phases:
            session.completed_phases.append(session.current_phase)
        
        # Advance to next phase
        phase_order = [
            AnalysisPhase.MIGRATION_SCOPE,
            AnalysisPhase.COST_ESTIMATES,
            AnalysisPhase.MODERNIZATION,
            AnalysisPhase.REPORT_GENERATION
        ]
        
        try:
            current_index = phase_order.index(session.current_phase)
            if current_index < len(phase_order) - 1:
                session.current_phase = phase_order[current_index + 1]
                session.updated_at = datetime.utcnow()
                
                return PhaseAdvanceResponse(
                    session_id=session_id,
                    current_phase=session.current_phase,
                    completed_phases=session.completed_phases,
                    success=True,
                    message=f"Advanced to {session.current_phase.value}"
                )
            else:
                return PhaseAdvanceResponse(
                    session_id=session_id,
                    current_phase=session.current_phase,
                    completed_phases=session.completed_phases,
                    success=False,
                    message="Already at final phase"
                )
        except ValueError:
            return PhaseAdvanceResponse(
                session_id=session_id,
                current_phase=session.current_phase,
                completed_phases=session.completed_phases,
                success=False,
                message="Invalid current phase"
            )
    
    def navigate_to_phase(self, session_id: str, target_phase: AnalysisPhase) -> Optional[PhaseAdvanceResponse]:
        """Navigate to a specific phase (for back navigation)"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        # Only allow navigation to completed phases or current phase
        phase_order = [
            AnalysisPhase.MIGRATION_SCOPE,
            AnalysisPhase.COST_ESTIMATES,
            AnalysisPhase.MODERNIZATION,
            AnalysisPhase.REPORT_GENERATION
        ]
        
        current_index = phase_order.index(session.current_phase)
        target_index = phase_order.index(target_phase)
        
        # Allow navigation to any completed phase or current phase
        if target_phase in session.completed_phases or target_phase == session.current_phase:
            session.current_phase = target_phase
            session.updated_at = datetime.utcnow()
            
            return PhaseAdvanceResponse(
                session_id=session_id,
                current_phase=session.current_phase,
                completed_phases=session.completed_phases,
                success=True,
                message=f"Navigated to {target_phase.value}"
            )
        else:
            return PhaseAdvanceResponse(
                session_id=session_id,
                current_phase=session.current_phase,
                completed_phases=session.completed_phases,
                success=False,
                message=f"Cannot navigate to {target_phase.value} - phase not completed"
            )
    
    def update_session_data(self, session_id: str, phase: AnalysisPhase, data: Dict[str, Any]) -> bool:
        """Update session with phase-specific data"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        # Store phase data (in production, this would be in database)
        # For now, we'll just update the timestamp
        session.updated_at = datetime.utcnow()
        return True
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    def list_sessions(self, user_id: Optional[str] = None) -> List[SessionStatusResponse]:
        """List all sessions (optionally filtered by user)"""
        sessions = []
        for session in self._sessions.values():
            if user_id is None or session.user_id == user_id:
                status = self.get_session_status(session.session_id)
                if status:
                    sessions.append(status)
        return sessions
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up expired sessions"""
        from datetime import timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        expired_sessions = []
        
        for session_id, session in self._sessions.items():
            if session.updated_at < cutoff_time:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self._sessions[session_id]
        
        return len(expired_sessions)
    
    def store_migration_scope_analysis(self, session_id: str, analysis_data: Dict[str, Any]) -> bool:
        """
        Store Migration Scope analysis results for cross-phase integration
        
        Args:
            session_id: Session identifier
            analysis_data: Migration Scope analysis results
            
        Returns:
            True if stored successfully, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.migration_scope_analysis = analysis_data
        session.updated_at = datetime.utcnow()
        return True
    
    def get_migration_scope_analysis(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve stored Migration Scope analysis results
        
        Args:
            session_id: Session identifier
            
        Returns:
            Migration Scope analysis data if available, None otherwise
        """
        session = self.get_session(session_id)
        if not session:
            return None
        
        return session.migration_scope_analysis
    
    def has_migration_scope_analysis(self, session_id: str) -> bool:
        """
        Check if Migration Scope analysis results are available
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if analysis data exists, False otherwise
        """
        analysis = self.get_migration_scope_analysis(session_id)
        return analysis is not None and len(analysis) > 0

# Global session manager instance
session_manager = SessionManager()
