"""
Phase Management Router
Handles session lifecycle and phase navigation for the enhanced UX platform
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import models and services with absolute imports
from ..models.core_models import (
    AnalysisPhase,
    SessionStatusResponse,
    PhaseAdvanceResponse,
    ErrorResponse
    )
from ..services.session_manager import session_manager

# Create router
phase_router = APIRouter(prefix="/api/phases", tags=["Phase Management"])

@phase_router.post("/start-analysis")
async def start_analysis_session(vm_inventory: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Start a new multi-phase analysis session
    
    Args:
        vm_inventory: List of VM data from RVTools export
        
    Returns:
        Session information with session_id and initial phase
    """
    try:
        if not vm_inventory:
            raise HTTPException(
                status_code=400, 
                detail="VM inventory cannot be empty"
            )
        
        session_id = session_manager.create_session(vm_inventory)
        
        return {
            "session_id": session_id,
            "current_phase": AnalysisPhase.MIGRATION_SCOPE.value,
            "total_vms": len(vm_inventory),
            "message": "Analysis session started successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start analysis session: {str(e)}"
        )

@phase_router.get("/session/{session_id}")
async def get_session_status(session_id: str) -> SessionStatusResponse:
    """
    Get current session status and progress
    
    Args:
        session_id: Unique session identifier
        
    Returns:
        Current session status including phase and progress
    """
    status = session_manager.get_session_status(session_id)
    
    if not status:
        raise HTTPException(
            status_code=404, 
            detail="Session not found"
        )
    
    return status

@phase_router.post("/session/{session_id}/advance")
async def advance_to_next_phase(
    session_id: str, 
    completed_phase_data: Optional[Dict[str, Any]] = None
) -> PhaseAdvanceResponse:
    """
    Advance to the next phase and save current phase data
    
    Args:
        session_id: Unique session identifier
        completed_phase_data: Optional data from completed phase
        
    Returns:
        Phase advancement result
    """
    # Validate session exists
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404, 
            detail="Session not found"
        )
    
    # Save phase data if provided
    if completed_phase_data:
        session_manager.update_session_data(
            session_id, 
            session.current_phase, 
            completed_phase_data
        )
    
    # Advance phase
    result = session_manager.advance_phase(session_id, completed_phase_data)
    
    if not result:
        raise HTTPException(
            status_code=500,
            detail="Failed to advance phase"
        )
    
    return result

@phase_router.post("/session/{session_id}/navigate")
async def navigate_to_phase(
    session_id: str, 
    target_phase: AnalysisPhase
) -> PhaseAdvanceResponse:
    """
    Navigate to a specific phase (for back navigation)
    
    Args:
        session_id: Unique session identifier
        target_phase: Target phase to navigate to
        
    Returns:
        Navigation result
    """
    result = session_manager.navigate_to_phase(session_id, target_phase)
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )
    
    if not result.success:
        raise HTTPException(
            status_code=400,
            detail=result.message
        )
    
    return result

@phase_router.get("/sessions")
async def list_sessions(user_id: Optional[str] = None) -> List[SessionStatusResponse]:
    """
    List all analysis sessions (optionally filtered by user)
    
    Args:
        user_id: Optional user ID filter
        
    Returns:
        List of session status objects
    """
    return session_manager.list_sessions(user_id)

@phase_router.delete("/session/{session_id}")
async def delete_session(session_id: str) -> Dict[str, str]:
    """
    Delete an analysis session
    
    Args:
        session_id: Unique session identifier
        
    Returns:
        Deletion confirmation
    """
    success = session_manager.delete_session(session_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )
    
    return {
        "message": "Session deleted successfully",
        "session_id": session_id
    }

@phase_router.post("/cleanup")
async def cleanup_expired_sessions(max_age_hours: int = 24) -> Dict[str, Any]:
    """
    Clean up expired sessions
    
    Args:
        max_age_hours: Maximum age in hours before session expires
        
    Returns:
        Cleanup results
    """
    try:
        deleted_count = session_manager.cleanup_expired_sessions(max_age_hours)
        
        return {
            "message": "Session cleanup completed",
            "deleted_sessions": deleted_count,
            "max_age_hours": max_age_hours,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup sessions: {str(e)}"
        )

@phase_router.get("/health")
async def phase_management_health() -> Dict[str, Any]:
    """
    Health check for phase management service
    
    Returns:
        Service health status
    """
    try:
        active_sessions = len(session_manager.list_sessions())
        
        return {
            "status": "healthy",
            "service": "phase_management",
            "active_sessions": active_sessions,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "phase_management",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
